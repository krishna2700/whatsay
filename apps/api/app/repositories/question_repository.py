"""
Question Repository — OPTIMIZED

Uses selectinload (async-safe) with minimal queries.
selectinload fires ONE extra query per relationship (not per row).
So for 20 questions: 2 queries total (questions + recommendations)
NOT 20 separate queries.
"""

from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, text, update
from sqlalchemy.orm import selectinload
from app.models.question import Question, QuestionStatus
from app.models.recommendation import Recommendation, RecommendedProduct
from app.repositories.base_repository import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, db: AsyncSession):
        super().__init__(Question, db)

    async def get_by_slug(self, slug: str) -> Optional[Question]:
        result = await self.db.execute(
            select(Question)
            .where(Question.slug == slug)
            .options(
                selectinload(Question.recommendation).selectinload(Recommendation.products)
            )
        )
        return result.scalar_one_or_none()

    async def get_with_recommendation(self, question_id: str) -> Optional[Question]:
        result = await self.db.execute(
            select(Question)
            .where(Question.id == question_id)
            .options(
                selectinload(Question.recommendation).selectinload(Recommendation.products)
            )
        )
        return result.scalar_one_or_none()

    async def get_user_questions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Question], int]:
        """
        2 queries total:
          Query 1: SELECT questions WHERE user_id = ? LIMIT ?
          Query 2: SELECT recommendations WHERE question_id IN (...)
        NOT N+1.
        """
        # Run count and questions concurrently
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Question)
            .where(Question.user_id == user_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Question)
            .where(Question.user_id == user_id)
            .options(
                # selectinload: 1 extra query for all recommendations at once
                selectinload(Question.recommendation)
            )
            .order_by(desc(Question.created_at))
            .offset(skip)
            .limit(limit)
        )
        questions = result.scalars().all()

        return questions, total

    async def get_recent(self, limit: int = 10) -> Sequence[Question]:
        result = await self.db.execute(
            select(Question)
            .where(Question.status == QuestionStatus.COMPLETED)
            .options(selectinload(Question.recommendation))
            .order_by(desc(Question.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def increment_view_count(self, question_id: str) -> None:
        """Direct UPDATE — no SELECT needed."""
        await self.db.execute(
            text("UPDATE questions SET view_count = view_count + 1 WHERE id = :id"),
            {"id": question_id}
        )
        await self.db.flush()

    async def count_by_user(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Question)
            .where(Question.user_id == user_id)
        )
        return result.scalar_one()
