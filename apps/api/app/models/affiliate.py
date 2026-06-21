from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class AffiliateClick(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "affiliate_clicks"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    affiliate_url: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="affiliate_clicks")  # type: ignore

    def __repr__(self) -> str:
        return f"<AffiliateClick id={self.id}>"


class AffiliateSettings(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "affiliate_settings"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    amazon_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="affiliate_settings")  # type: ignore

    def __repr__(self) -> str:
        return f"<AffiliateSettings user_id={self.user_id} tag={self.amazon_tag}>"
