from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.dependencies import get_db, get_current_user, get_optional_user
from app.models.user import User
from app.models.affiliate import AffiliateClick, AffiliateSettings
from app.affiliate.service import AffiliateService
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/affiliate", tags=["Affiliate"])


class TrackClickRequest(BaseModel):
    question_id: str
    product_id: Optional[str] = None
    affiliate_url: str


class GenerateUrlRequest(BaseModel):
    product_url: str
    tag: Optional[str] = None


class UpdateSettingsRequest(BaseModel):
    amazon_tag: str


@router.post("/click", status_code=status.HTTP_201_CREATED)
async def track_click(
    data: TrackClickRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    click = AffiliateClick(
        user_id=current_user.id if current_user else None,
        question_id=data.question_id,
        product_id=data.product_id,
        affiliate_url=data.affiliate_url,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )
    db.add(click)
    await db.flush()
    return {"success": True, "click_id": click.id}


@router.post("/generate-url")
async def generate_affiliate_url(
    data: GenerateUrlRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService()
    tag = data.tag or settings.AMAZON_AFFILIATE_TAG

    # Use user's custom tag if available
    if current_user and current_user.affiliate_settings:
        tag = current_user.affiliate_settings.amazon_tag

    url = service.build_affiliate_url(data.product_url, tag)
    return {"url": url, "tag": tag}


@router.get("/settings")
async def get_affiliate_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.affiliate_settings:
        return {
            "amazon_tag": settings.AMAZON_AFFILIATE_TAG,
            "is_active": False,
            "is_custom": False,
        }
    return {
        "amazon_tag": current_user.affiliate_settings.amazon_tag,
        "is_active": current_user.affiliate_settings.is_active,
        "is_custom": True,
    }


@router.put("/settings")
async def update_affiliate_settings(
    data: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.affiliate_settings:
        current_user.affiliate_settings.amazon_tag = data.amazon_tag
        await db.flush()
    else:
        settings_obj = AffiliateSettings(
            user_id=current_user.id,
            amazon_tag=data.amazon_tag,
        )
        db.add(settings_obj)
        await db.flush()

    return {"success": True, "amazon_tag": data.amazon_tag}
