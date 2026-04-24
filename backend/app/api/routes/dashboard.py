from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models import Enrollment, ProgressLog
from app.services.dashboard import get_dashboard_overview_with_roadmap


router = APIRouter()


@router.get("/api/dashboard/overview")
def overview(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    if not user_id:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    return get_dashboard_overview_with_roadmap(db, user_id)


@router.get("/api/dashboard/summary")
def summary(userId: int = Query(default=1), db: Session = Depends(get_db)):
    completed = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.user_id == userId, Enrollment.progress_percent >= 100)) or 0
    in_progress = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.user_id == userId, Enrollment.progress_percent > 0, Enrollment.progress_percent < 100)) or 0
    return {"completed": completed, "inProgress": in_progress}


@router.get("/api/dashboard/courses")
def courses(userId: int = Query(default=1), db: Session = Depends(get_db)):
    enrollments = db.scalars(select(Enrollment).where(Enrollment.user_id == userId)).all()
    return [
        {
            "id": enrollment.course_id,
            "title": enrollment.course.title if enrollment.course else "",
            "author": enrollment.course.author if enrollment.course else "",
            "rating": float(enrollment.course.rating) if enrollment.course else 0,
            "progress": enrollment.progress_percent,
        }
        for enrollment in enrollments
    ]


@router.get("/api/dashboard/weekly-hours")
def weekly_hours(userId: int = Query(default=1), db: Session = Depends(get_db)):
    from_utc = datetime.utcnow().date() - timedelta(days=6)
    logs = db.scalars(select(ProgressLog).where(ProgressLog.user_id == userId, ProgressLog.created_at_utc >= from_utc)).all()
    keys = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    values = {key: 0 for key in keys}
    for log in logs:
        key = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][log.created_at_utc.weekday()]
        values[key] += round(log.minutes_learned / 60)
    return [{"day": key, "hours": values[key]} for key in keys]
