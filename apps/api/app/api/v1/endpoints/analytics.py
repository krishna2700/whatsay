"""
Analytics Endpoints

Tracks the full funnel:
  Question Asked
  → Recommendation Generated
  → Affiliate Click (user trusted the recommendation)
  → Purchase (tracked via Amazon Associates dashboard)

Key KPI: Trust Score = Clicks / Recommendations
This tells us: are users trusting WhatSay's recommendations enough to buy?
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import date, timedelta
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.question import Question
from app.models.recommendation import Recommendation
from app.models.affiliate import AffiliateClick
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    CategoryStat,
    TimeSeriesData,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryResponse:

    # Total questions
    q_count = await db.execute(
        select(func.count()).select_from(Question).where(Question.user_id == current_user.id)
    )
    total_questions = q_count.scalar_one()

    # Total recommendations
    rec_count = await db.execute(
        select(func.count()).select_from(Recommendation).join(Question).where(
            Question.user_id == current_user.id
        )
    )
    total_recommendations = rec_count.scalar_one()

    # Total affiliate clicks
    click_count = await db.execute(
        select(func.count()).select_from(AffiliateClick).where(
            AffiliateClick.user_id == current_user.id
        )
    )
    total_clicks = click_count.scalar_one()

    # Trust Score = (affiliate clicks / recommendations) * 100
    # This is the KEY metric — how often do users trust the recommendation enough to click Buy?
    trust_score = (total_clicks / total_recommendations * 100) if total_recommendations > 0 else 0.0

    # Questions today
    today = date.today()
    q_today = await db.execute(
        select(func.count()).select_from(Question).where(
            Question.user_id == current_user.id,
            func.date(Question.created_at) == today,
        )
    )
    questions_today = q_today.scalar_one()

    # Clicks today
    c_today = await db.execute(
        select(func.count()).select_from(AffiliateClick).where(
            AffiliateClick.user_id == current_user.id,
            func.date(AffiliateClick.created_at) == today,
        )
    )
    clicks_today = c_today.scalar_one()

    # Top categories
    cat_result = await db.execute(
        select(Question.category, func.count().label("count"))
        .where(Question.user_id == current_user.id, Question.category.isnot(None))
        .group_by(Question.category)
        .order_by(desc("count"))
        .limit(5)
    )
    categories_raw = cat_result.all()
    total_cat = sum(r.count for r in categories_raw) or 1
    top_categories = [
        CategoryStat(
            category=r.category,
            count=r.count,
            percentage=round(r.count / total_cat * 100, 1),
        )
        for r in categories_raw
    ]

    # Questions over time (last 30 days)
    questions_over_time = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_count = await db.execute(
            select(func.count()).select_from(Question).where(
                Question.user_id == current_user.id,
                func.date(Question.created_at) == day,
            )
        )
        questions_over_time.append(
            TimeSeriesData(date=day.strftime("%b %d"), value=day_count.scalar_one())
        )

    # Clicks over time (last 30 days)
    clicks_over_time = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_count = await db.execute(
            select(func.count()).select_from(AffiliateClick).where(
                AffiliateClick.user_id == current_user.id,
                func.date(AffiliateClick.created_at) == day,
            )
        )
        clicks_over_time.append(
            TimeSeriesData(date=day.strftime("%b %d"), value=day_count.scalar_one())
        )

    return AnalyticsSummaryResponse(
        total_questions=total_questions,
        total_recommendations=total_recommendations,
        total_affiliate_clicks=total_clicks,
        total_users=1,
        ctr=round(trust_score, 2),  # Trust Score replaces generic CTR
        questions_today=questions_today,
        clicks_today=clicks_today,
        top_categories=top_categories,
        top_products=[],
        questions_over_time=questions_over_time,
        clicks_over_time=clicks_over_time,
    )
