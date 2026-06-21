from fastapi import APIRouter
from app.api.v1.endpoints import auth, questions, affiliate, analytics

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(questions.router)
api_router.include_router(affiliate.router)
api_router.include_router(analytics.router)
