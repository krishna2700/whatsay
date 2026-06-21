from pydantic import BaseModel
from typing import Optional


class CategoryStat(BaseModel):
    category: str
    count: int
    percentage: float


class ProductStat(BaseModel):
    product_id: str
    product_name: str
    click_count: int
    question_count: int


class TimeSeriesData(BaseModel):
    date: str
    value: int


class AnalyticsSummaryResponse(BaseModel):
    total_questions: int
    total_recommendations: int
    total_affiliate_clicks: int
    total_users: int
    ctr: float
    questions_today: int
    clicks_today: int
    top_categories: list[CategoryStat]
    top_products: list[ProductStat]
    questions_over_time: list[TimeSeriesData]
    clicks_over_time: list[TimeSeriesData]
