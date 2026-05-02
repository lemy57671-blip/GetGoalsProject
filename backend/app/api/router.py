from fastapi import APIRouter

from app.api.routes import (
    attempts,
    auth,
    chat,
    dashboard,
    diagnostic,
    flashcards,
    health,
    me,
    payments,
    progress,
    review,
    roadmap,
    settings,
    subscription,
    toeic,
    translate,
    tts,
    users,
    weekly_check,
)

api_router = APIRouter()

# Các file route này đã tự có /api/... bên trong
# nên KHÔNG thêm prefix ở đây, tránh bị /api/auth/api/auth...
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(users.router)
api_router.include_router(settings.router)

api_router.include_router(dashboard.router)
api_router.include_router(progress.router)
api_router.include_router(roadmap.router)
api_router.include_router(weekly_check.router)
api_router.include_router(review.router)

api_router.include_router(toeic.router)
api_router.include_router(diagnostic.router)
api_router.include_router(attempts.router)

api_router.include_router(subscription.router)
api_router.include_router(payments.router)

# Riêng chat.py đang có @router.post("") hoặc @router.post("/")
# nên bắt buộc include với prefix để endpoint thành /api/chat.
api_router.include_router(chat.router, prefix="/api/chat", tags=["chat"])

# Các route mới từ nhánh local/HEAD
api_router.include_router(flashcards.router)
api_router.include_router(tts.router, tags=["tts"])
api_router.include_router(translate.router, tags=["translate"])