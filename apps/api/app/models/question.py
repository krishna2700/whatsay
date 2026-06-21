from sqlalchemy import String, Text, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import UUIDMixin, TimestampMixin
import enum


class QuestionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Question(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "questions"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    status: Mapped[QuestionStatus] = mapped_column(
        SAEnum(QuestionStatus), default=QuestionStatus.PENDING, nullable=False
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    # Engagement
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="questions")  # type: ignore
    recommendation: Mapped["Recommendation | None"] = relationship(  # type: ignore
        "Recommendation", back_populates="question", uselist=False, lazy="select"
    )
    affiliate_clicks: Mapped[list["AffiliateClick"]] = relationship(  # type: ignore
        "AffiliateClick", back_populates="question", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} text={self.text[:50]}>"
