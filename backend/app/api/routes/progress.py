from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models import Enrollment, ProgressLog
from app.schemas.analytics import HistoryPointDto, ProgressSummaryDto
from app.schemas.progress import ProgressLogRequest
from app.services.learning_analytics import get_progress_history, get_progress_summary


router = APIRouter()


@router.get("/api/progress/summary")
def summary(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    if not user_id:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    try:
        return get_progress_summary(db, user_id)
    except SQLAlchemyError:
        db.rollback()
        return ProgressSummaryDto(weeklyStudyMinutes=_empty_history_points(7))


@router.get("/api/progress/history")
def history(days: int = Query(default=30), db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    if not user_id:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    try:
        return get_progress_history(db, user_id, days)
    except SQLAlchemyError:
        db.rollback()
        return _empty_history_points(days)


def _empty_history_points(days: int) -> list[HistoryPointDto]:
    normalized_days = max(1, min(days, 90))
    from_date = datetime.utcnow().date() - timedelta(days=normalized_days - 1)
    return [
        HistoryPointDto(date=(from_date + timedelta(days=index)).strftime("%Y-%m-%d"))
        for index in range(normalized_days)
    ]


@router.post("/api/progress/log")
def log_progress(payload: ProgressLogRequest, userId: int = Query(default=1), db: Session = Depends(get_db)):
    course_id = payload.courseId
    minutes_learned = payload.minutesLearned
    progress_delta = payload.progressDelta
    if course_id <= 0:
        return PlainTextResponse("courseId invalid", status_code=400)
    if minutes_learned < 0:
        return PlainTextResponse("minutesLearned invalid", status_code=400)
    enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == userId, Enrollment.course_id == course_id))
    if enrollment is None:
        return PlainTextResponse("enrollment not found", status_code=404)
    enrollment.progress_percent = max(0, min(enrollment.progress_percent + progress_delta, 100))
    db.add(
        ProgressLog(
            user_id=userId,
            course_id=course_id,
            minutes_learned=minutes_learned,
            progress_delta=progress_delta,
            created_at_utc=datetime.utcnow(),
        )
    )
    db.commit()
    completed = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.user_id == userId, Enrollment.progress_percent >= 100)) or 0
    in_progress = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.user_id == userId, Enrollment.progress_percent < 100)) or 0
    from_utc = datetime.utcnow().date() - timedelta(days=6)
    logs = db.scalars(select(ProgressLog).where(ProgressLog.user_id == userId, ProgressLog.created_at_utc >= from_utc)).all()
    keys = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    values = {key: 0 for key in keys}
    for log in logs:
        key = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][log.created_at_utc.astimezone().weekday() if log.created_at_utc.tzinfo else log.created_at_utc.weekday()]
        values[key] += round(log.minutes_learned / 60)
    return {
        "updatedCourse": {
            "id": enrollment.course_id,
            "title": enrollment.course.title if enrollment.course else "",
            "author": enrollment.course.author if enrollment.course else "",
            "rating": float(enrollment.course.rating) if enrollment.course else 0,
            "progress": enrollment.progress_percent,
        },
        "summary": {"completed": completed, "inProgress": in_progress},
        "weeklyHours": [{"day": key, "hours": values[key]} for key in keys],
    }
