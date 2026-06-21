from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import UUIDMixin, TimestampMixin
import enum


class RecommendationVerdict(str, enum.Enum):
    HIGHLY_RECOMMENDED = "highly_recommended"
    RECOMMENDED = "recommended"
    NEUTRAL = "neutral"
    NOT_RECOMMENDED = "not_recommended"
    AVOID = "avoid"


class Recommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recommendations"

    question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    verdict: Mapped[RecommendationVerdict] = mapped_column(
        SAEnum(RecommendationVerdict), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    pros: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    cons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    ai_model: Mapped[str] = mapped_column(String(100), nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Trust Score / Recommendation Quality Tracking ─────────────────────────
    # Tracks: Question → Recommendation → Click → (Purchase if available)
    # This is the real KPI: can users trust the recommendation enough to click Buy?
    affiliate_click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    helpful_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_helpful_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # trust_score = (clicks + helpful) / views — computed property
    product_source: Mapped[str] = mapped_column(
        String(20), default="serpapi", nullable=False
    )  # "serpapi" | "paapi" | "none"

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="recommendation")  # type: ignore
    products: Mapped[list["RecommendedProduct"]] = relationship(
        "RecommendedProduct",
        back_populates="recommendation",
        order_by="RecommendedProduct.rank",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} verdict={self.verdict}>"


class RecommendedProduct(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recommended_products"

    recommendation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    amazon_url: Mapped[str] = mapped_column(Text, nullable=False)
    affiliate_url: Mapped[str] = mapped_column(Text, nullable=False)
    asin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    specs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    why_recommended: Mapped[str | None] = mapped_column(Text, nullable=True)
    rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_alternative: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation", back_populates="products"
    )

    def __repr__(self) -> str:
        return f"<RecommendedProduct id={self.id} name={self.name[:30]}>"
