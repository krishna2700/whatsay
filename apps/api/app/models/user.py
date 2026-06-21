from sqlalchemy import String, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Auth
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # OAuth
    google_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Stats
    questions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    questions: Mapped[list["Question"]] = relationship(  # type: ignore
        "Question", back_populates="user", lazy="select"
    )
    affiliate_settings: Mapped["AffiliateSettings | None"] = relationship(  # type: ignore
        "AffiliateSettings", back_populates="user", uselist=False, lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
