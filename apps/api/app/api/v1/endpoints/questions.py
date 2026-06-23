"""
Questions API Endpoints

All recommendations go through mandatory Amazon product validation.
"""

import json
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from app.core.dependencies import get_db, get_current_user, get_optional_user
from app.models.user import User
from app.models.question import Question
from app.models.recommendation import Recommendation, RecommendedProduct
from app.services.question_service import QuestionService
from app.schemas.question import (
    AskQuestionRequest,
    AskQuestionResponse,
    QuestionResponse,
    RecommendationResponse,
    RecommendedProductResponse,
    PaginatedQuestionsResponse,
)
from app.core.config import settings

router = APIRouter(prefix="/questions", tags=["Questions"])


def _build_question_response(question: Question, include_products: bool = False) -> QuestionResponse:
    """Build QuestionResponse — only access already-loaded relationships."""
    rec_response = None
    if question.recommendation:
        rec = question.recommendation
        # Only load products if explicitly requested (detail view)
        # For list view, skip products to avoid lazy loading
        products = []
        if include_products and rec.products:
            products = [
                RecommendedProductResponse(
                    id=p.id,
                    name=p.name,
                    brand=p.brand,
                    category=p.category,
                    price=p.price,
                    currency=p.currency,
                    rating=p.rating,
                    review_count=p.review_count,
                    image_url=p.image_url,
                    amazon_url=p.amazon_url,
                    affiliate_url=p.affiliate_url,
                    asin=p.asin,
                    specs=p.specs or {},
                    why_recommended=p.why_recommended,
                    rank=p.rank,
                    is_alternative=p.is_alternative,
                )
                for p in rec.products
            ]
        rec_response = RecommendationResponse(
            id=rec.id,
            question_id=rec.question_id,
            verdict=rec.verdict,
            summary=rec.summary,
            detailed_analysis=rec.detailed_analysis,
            pros=rec.pros or [],
            cons=rec.cons or [],
            score=rec.score,
            confidence=rec.confidence,
            ai_model=rec.ai_model,
            created_at=rec.created_at,
            products=products,
        )

    return QuestionResponse(
        id=question.id,
        user_id=question.user_id,
        text=question.text,
        slug=question.slug,
        status=question.status,
        category=question.category,
        intent=question.intent,
        view_count=question.view_count,
        helpful_count=question.helpful_count,
        created_at=question.created_at,
        updated_at=question.updated_at,
        recommendation=rec_response,
    )


@router.post("/ask", response_model=AskQuestionResponse, status_code=status.HTTP_201_CREATED)
async def ask_question(
    data: AskQuestionRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> AskQuestionResponse:
    service = QuestionService(db)
    affiliate_tag = settings.AMAZON_AFFILIATE_TAG

    question = await service.ask_question(
        data=data,
        user_id=current_user.id if current_user else None,
        affiliate_tag=affiliate_tag,
    )

    # include_products=True for ask — user needs full product cards
    q_response = _build_question_response(question, include_products=True)
    return AskQuestionResponse(
        question=q_response,
        recommendation=q_response.recommendation,
    )


@router.post("/ask/stream")
async def ask_question_stream(
    data: AskQuestionRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream AI response then return full recommendation."""
    service = QuestionService(db)

    async def generate():
        # Stream conversational response
        async for chunk in service.stream_question(data, current_user.id if current_user else None):
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        # Generate full recommendation
        try:
            affiliate_tag = settings.AMAZON_AFFILIATE_TAG
            question = await service.ask_question(
                data=data,
                user_id=current_user.id if current_user else None,
                affiliate_tag=affiliate_tag,
            )
            q_response = _build_question_response(question, include_products=True)
            response_data = AskQuestionResponse(
                question=q_response,
                recommendation=q_response.recommendation,
            )
            yield f"data: {json.dumps({'type': 'complete', 'data': response_data.model_dump(mode='json')})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("", response_model=PaginatedQuestionsResponse)
async def get_user_questions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedQuestionsResponse:
    from sqlalchemy import func, desc, select, text
    from app.models.question import Question
    from sqlalchemy.orm import selectinload

    skip = (page - 1) * per_page

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(Question).where(Question.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    # Fetch with eager loaded recommendations
    result = await db.execute(
        select(Question)
        .where(Question.user_id == current_user.id)
        .options(selectinload(Question.recommendation))
        .order_by(desc(Question.created_at))
        .offset(skip)
        .limit(per_page)
    )
    questions = result.scalars().all()
    total_pages = (total + per_page - 1) // per_page

    return PaginatedQuestionsResponse(
        data=[_build_question_response(q) for q in questions],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/recent", response_model=list[QuestionResponse])
async def get_recent_questions(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[QuestionResponse]:
    from app.repositories.question_repository import QuestionRepository
    repo = QuestionRepository(db)
    questions = await repo.get_recent(limit=limit)
    return [_build_question_response(q) for q in questions]


@router.get("/slug/{slug}", response_model=QuestionResponse)
async def get_question_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    service = QuestionService(db)
    question = await service.get_question_by_slug(slug)
    return _build_question_response(question, include_products=True)


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    service = QuestionService(db)
    question = await service.get_question(question_id)
    return _build_question_response(question, include_products=True)


@router.post("/{question_id}/helpful", status_code=status.HTTP_204_NO_CONTENT)
async def mark_helpful(
    question_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    from app.repositories.question_repository import QuestionRepository
    repo = QuestionRepository(db)
    question = await repo.get_by_id(question_id)
    if question:
        question.helpful_count += 1
        await db.flush()
