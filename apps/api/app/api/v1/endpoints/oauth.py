"""
Google OAuth Authentication

Flow:
  1. Frontend triggers Google OAuth popup (@react-oauth/google)
  2. Google returns access_token to frontend
  3. Frontend fetches user info from Google userinfo endpoint
  4. Frontend sends user info + access_token to POST /auth/google/token
  5. Backend verifies with Google, creates/finds user, returns JWT
  6. Frontend stores JWT, user is logged in ✅
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx
from app.core.dependencies import get_db
from app.core.config import settings
from app.services.auth_service import AuthService
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["OAuth"])

GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_TOKEN_INFO_URL = "https://www.googleapis.com/oauth2/v3/tokeninfo"


class GoogleTokenRequest(BaseModel):
    access_token: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    email_verified: Optional[bool] = True


class OAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 604800
    user: dict


@router.post("/google/token", response_model=OAuthResponse)
async def google_oauth_token(
    data: GoogleTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> OAuthResponse:
    """
    Verify Google access token and return WhatSay JWT.
    """
    try:
        # Verify the access token with Google and get fresh user info
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {data.access_token}"},
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google access token",
            )

        google_info = response.json()

        # Extract verified user info from Google
        google_id = google_info.get("sub") or data.google_id
        email = google_info.get("email") or data.email
        name = google_info.get("name") or data.name or (email.split("@")[0] if email else "User")
        avatar_url = google_info.get("picture") or data.avatar_url
        email_verified = google_info.get("email_verified", True)

        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get user info from Google",
            )

        # Create or find user in database
        service = AuthService(db)
        user, token = await service.get_or_create_oauth_user(
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=avatar_url,
        )

        logger.info("Google OAuth success", user_id=user.id, email=email)

        return OAuthResponse(
            access_token=token,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "is_verified": True,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Google OAuth failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed. Please try again.",
        )
