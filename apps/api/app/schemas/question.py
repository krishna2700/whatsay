from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.question import QuestionStatus
from app.models.recommendation import RecommendationVerdict


class AskQuestionRequest(BaseModel):
    text: str = Field(min_length=5, max_length=500)
    budget: Optional[int] = Field(None, gt=0)
    currency: Optional[str] = Field("INR", max_length=10)
    category: Optional[str] = None


class RecommendedProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    brand: str
    category: str
    price: float
    currency: str
    rating: float
    review_count: int
    image_url: Optional[str] = None
    amazon_url: str
    affiliate_url: str
    asin: Optional[str] = None
    specs: dict
    why_recommended: Optional[str] = None
    rank: int
    is_alternative: bool


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question_id: str
    verdict: RecommendationVerdict
    summary: str
    detailed_analysis: Optional[str] = None
    pros: list[str]
    cons: list[str]
    score: int
    confidence: int
    ai_model: str
    created_at: datetime
    products: list[RecommendedProductResponse] = []

    @property
    def alternatives(self) -> list[RecommendedProductResponse]:
        return [p for p in self.products if p.is_alternative]

    @property
    def main_products(self) -> list[RecommendedProductResponse]:
        return [p for p in self.products if not p.is_alternative]


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    text: str
    slug: str
    status: QuestionStatus
    category: Optional[str] = None
    intent: Optional[str] = None
    view_count: int
    helpful_count: int
    created_at: datetime
    updated_at: datetime
    recommendation: Optional[RecommendationResponse] = None


class AskQuestionResponse(BaseModel):
    question: QuestionResponse
    recommendation: Optional[RecommendationResponse] = None


class PaginatedQuestionsResponse(BaseModel):
    data: list[QuestionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
