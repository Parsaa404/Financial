"""V1 API router — includes all sub-routers."""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.decision import router as decision_router
from app.api.v1.forecast import router as forecast_router
from app.api.v1.goals import router as goals_router
from app.api.v1.insights import router as insights_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(decision_router)
api_v1_router.include_router(forecast_router)
api_v1_router.include_router(goals_router)
api_v1_router.include_router(insights_router)
