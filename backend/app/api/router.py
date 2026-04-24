from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import weekly_check
from app.api.routes import attempts, auth, chat, dashboard, diagnostic, health, me, payments, progress, review, roadmap, subscription, toeic, users


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(subscription.router)
api_router.include_router(me.router)
api_router.include_router(review.router)
api_router.include_router(diagnostic.router)
api_router.include_router(toeic.router)
api_router.include_router(attempts.router)
api_router.include_router(weekly_check.router)
api_router.include_router(roadmap.router)
api_router.include_router(dashboard.router)
api_router.include_router(progress.router)
api_router.include_router(payments.router)
api_router.include_router(chat.router)
