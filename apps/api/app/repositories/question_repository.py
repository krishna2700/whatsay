from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from app.models.question import Question, QuestionStatus
from app.models.recommendation import Recommendation
from app.repositories.base_repository import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, db: AsyncSession):
        super().__init__(Question, db)

    async def get_by_slug(self, slug: str) -> Optional[Question]:
        result = await self.db.execute(
            select(Question)
            .where(Question.slug == slug)
            .options(selectinload(Question.recommendation).selectinload(Recommendation.products))
        )
        return result.scalar_one_or_none()

    async def get_with_recommendation(self, question_id: str) -> Optional[Question]:
        result = await self.db.execute(
            select(Question)
            .where(Question.id == question_id)
            .options(selectinload(Question.recommendation).selectinload(Recommendation.products))
        )
        return result.scalar_one_or_none()

    async def get_user_questions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Question], int]:
        # Get questions
        result = await self.db.execute(
            select(Question)
            .where(Question.user_id == user_id)
            .options(selectinload(Question.recommendation))
            .order_by(desc(Question.created_at))
            .offset(skip)
            .limit(limit)
        )
        questions = result.scalars().all()

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(Question).where(Question.user_id == user_id)
        )
        total = count_result.scalar_one()

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
        question = await self.get_by_id(question_id)
        if question:
            question.view_count += 1
            await self.db.flush()

    async def count_by_user(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Question).where(Question.user_id == user_id)
        )
        return result.scalar_one()

    async def count_today(self) -> int:
        from datetime import date
        from sqlalchemy import cast, Date
        result = await self.db.execute(
            select(func.count()).select_from(Question).where(
                cast(Question.created_at, Date) == date.today()
            )
        )
        return result.scalar_one()
