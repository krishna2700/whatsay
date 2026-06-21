from datetime import timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.core.config import settings
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
import structlog

logger = structlog.get_logger()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: RegisterRequest) -> tuple[User, str]:
        # Check if email exists
        if await self.user_repo.email_exists(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # Create user
        user = User(
            email=data.email,
            name=data.name,
            hashed_password=hash_password(data.password),
            is_active=True,
            is_verified=False,
        )

        user = await self.user_repo.create(user)
        token = create_access_token(
            subject=user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        logger.info("User registered", user_id=user.id, email=user.email)
        return user, token

    async def login(self, data: LoginRequest) -> tuple[User, str]:
        user = await self.user_repo.get_by_email(data.email)

        if not user or not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        token = create_access_token(
            subject=user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        logger.info("User logged in", user_id=user.id)
        return user, token

    async def get_or_create_oauth_user(
        self,
        email: str,
        name: str,
        google_id: str,
        avatar_url: Optional[str] = None,
    ) -> tuple[User, str]:
        # Check by Google ID first
        user = await self.user_repo.get_by_google_id(google_id)

        if not user:
            # Check by email
            user = await self.user_repo.get_by_email(email)
            if user:
                # Link Google account
                user.google_id = google_id
                user.oauth_provider = "google"
                if avatar_url:
                    user.avatar_url = avatar_url
                await self.user_repo.update(user)
            else:
                # Create new user
                user = User(
                    email=email,
                    name=name,
                    google_id=google_id,
                    oauth_provider="google",
                    avatar_url=avatar_url,
                    is_active=True,
                    is_verified=True,
                )
                user = await self.user_repo.create(user)

        token = create_access_token(subject=user.id)
        return user, token
