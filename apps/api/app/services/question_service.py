"""
Question Service — orchestrates the full recommendation flow.

Flow:
  1. Create question record
  2. Run Amazon validation + AI recommendation
  3. Persist recommendation + products
  4. Return complete question with recommendation
"""

import uuid
import re
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.question import Question, QuestionStatus
from app.models.recommendation import Recommendation, RecommendedProduct
from app.repositories.question_repository import QuestionRepository
from app.repositories.user_repository import UserRepository
from app.ai.recommendation_engine import RecommendationEngine
from app.ai.provider_factory import get_ai_provider
from app.core.config import settings
from app.schemas.question import AskQuestionRequest
import structlog

logger = structlog.get_logger()


def generate_slug(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')[:100]
    unique_id = str(uuid.uuid4())[:8]
    return f"{slug}-{unique_id}"


class QuestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.question_repo = QuestionRepository(db)
        self.user_repo = UserRepository(db)

    async def ask_question(
        self,
        data: AskQuestionRequest,
        user_id: Optional[str] = None,
        affiliate_tag: str = "whatsay-21",
    ) -> Question:
        # Create question record
        question = Question(
            user_id=user_id,
            text=data.text,
            slug=generate_slug(data.text),
            status=QuestionStatus.PROCESSING,
            budget=data.budget,
            currency=data.currency or "INR",
        )
        question = await self.question_repo.create(question)

        try:
            # Get AI provider and run full recommendation flow
            provider = get_ai_provider()
            engine = RecommendationEngine(provider)

            logger.info("Starting recommendation", question=data.text, question_id=question.id)

            result = await engine.generate_recommendation(
                question=data.text,
                budget=data.budget,
                currency=data.currency or "INR",
                affiliate_tag=affiliate_tag,
            )

            # Update question metadata
            question.category = result.category
            question.intent = result.intent
            question.status = QuestionStatus.COMPLETED

            # Create recommendation record
            recommendation = Recommendation(
                question_id=question.id,
                verdict=result.verdict,
                summary=result.summary,
                detailed_analysis=result.detailed_analysis,
                pros=result.pros,
                cons=result.cons,
                score=result.score,
                confidence=result.confidence,
                ai_model=provider.model_name,
                ai_provider=provider.provider_name,
            )
            self.db.add(recommendation)
            await self.db.flush()
            await self.db.refresh(recommendation)

            # Create recommended products (only Amazon-validated ones)
            all_products = [
                {**p, "is_alternative": False} for p in result.products
            ] + [
                {**p, "is_alternative": True} for p in result.alternatives
            ]

            for i, product_data in enumerate(all_products):
                # Only create product records with valid affiliate URLs
                affiliate_url = product_data.get("affiliate_url", "")
                amazon_url = product_data.get("amazon_url", "")

                if not amazon_url:
                    continue  # Skip products without Amazon URLs

                product = RecommendedProduct(
                    recommendation_id=recommendation.id,
                    name=product_data.get("name", ""),
                    brand=product_data.get("brand", ""),
                    category=product_data.get("category", result.category),
                    price=float(product_data.get("price", 0)),
                    currency=product_data.get("currency", "INR"),
                    rating=float(product_data.get("rating", 0)),
                    review_count=int(product_data.get("review_count", 0)),
                    image_url=product_data.get("image_url"),
                    amazon_url=amazon_url,
                    affiliate_url=affiliate_url,
                    asin=product_data.get("asin"),
                    specs=product_data.get("specs", {}),
                    why_recommended=product_data.get("why_recommended", ""),
                    rank=product_data.get("rank", i + 1),
                    is_alternative=product_data.get("is_alternative", False),
                )
                self.db.add(product)

            # Update user question count
            if user_id:
                await self.user_repo.increment_questions_count(user_id)

            await self.db.flush()

            # Reload with relationships
            question = await self.question_repo.get_with_recommendation(question.id)
            logger.info("Recommendation complete", question_id=question.id, verdict=result.verdict)
            return question

        except Exception as e:
            question.status = QuestionStatus.FAILED
            await self.db.flush()
            logger.error("Question processing failed", error=str(e), question_id=question.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate recommendation: {str(e)}",
            )

    async def stream_question(
        self,
        data: AskQuestionRequest,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream conversational AI response."""
        provider = get_ai_provider()
        engine = RecommendationEngine(provider)

        async for chunk in engine.stream_recommendation(
            question=data.text,
            budget=data.budget,
            currency=data.currency or "INR",
        ):
            yield chunk

    async def get_question(self, question_id: str) -> Question:
        question = await self.question_repo.get_with_recommendation(question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        await self.question_repo.increment_view_count(question_id)
        return question

    async def get_question_by_slug(self, slug: str) -> Question:
        question = await self.question_repo.get_by_slug(slug)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        return question
