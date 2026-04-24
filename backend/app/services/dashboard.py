from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UserSkillAnalytics
from app.schemas.analytics import DashboardOverviewDto, WeakMetricDto, WeakPartDto
from app.services.learning_analytics import get_dashboard_overview
from app.services.roadmap import get_current_roadmap
from app.services.skill_analytics import to_dto, to_title


logger = logging.getLogger(__name__)


def get_dashboard_overview_with_roadmap(db: Session, user_id: int) -> DashboardOverviewDto:
    overview = get_dashboard_overview(db, user_id)
    try:
        overview.activeRoadmap = get_current_roadmap(db, user_id)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Could not load active roadmap for user_id=%s: %s", user_id, exc)
        overview.activeRoadmap = None

    analytics = db.scalar(select(UserSkillAnalytics).where(UserSkillAnalytics.user_id == user_id))
    analytics_dto = to_dto(analytics)
    if analytics_dto.weakestSkill:
        breakdown = next((item for item in analytics_dto.skillBreakdown if item.code.lower() == analytics_dto.weakestSkill.lower()), None)
        overview.weakestSkill = WeakMetricDto(
            skill=analytics_dto.weakestSkillLabel or to_title(analytics_dto.weakestSkill),
            accuracy=breakdown.accuracy if breakdown else 0,
            attemptCount=breakdown.attemptCount if breakdown else 0,
        )
    if analytics_dto.weakestPart is not None:
        part_breakdown = next((item for item in analytics_dto.partBreakdown if item.part == analytics_dto.weakestPart), None)
        overview.weakestPart = WeakPartDto(
            part=analytics_dto.weakestPart,
            accuracy=part_breakdown.accuracy if part_breakdown else 0,
            attemptCount=part_breakdown.attemptCount if part_breakdown else 0,
        )
    return overview
