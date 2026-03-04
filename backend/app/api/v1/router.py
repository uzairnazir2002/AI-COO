from fastapi import APIRouter

from app.api.v1 import ai, alerts, analytics, auth, forecast, health, organizations, reports, runway, transactions

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(runway.router, prefix="", tags=["runway"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["forecast"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(health.router, prefix="", tags=["health"])
