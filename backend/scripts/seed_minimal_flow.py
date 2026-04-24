from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Course, Enrollment, User


DEFAULT_USER_ID = 1
PRO_TEST_EMAIL = "smoke.pro@getgoals.dev"
PRO_TEST_PASSWORD = "Password123"
COURSE_TITLE = "GetGoals Smoke Course"


def ensure_course(db) -> Course:
    course = db.query(Course).filter(Course.title == COURSE_TITLE).first()
    if course:
        return course

    course = Course(
        title=COURSE_TITLE,
        author="GetGoals",
        rating=5,
    )
    db.add(course)
    db.flush()
    return course


def ensure_user_enrollment(db, user_id: int, course_id: int) -> None:
    user = db.get(User, user_id)
    if not user:
        print(f"skip enrollment: user {user_id} not found")
        return

    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    if enrollment:
        print(f"enrollment already exists: user={user_id} course={course_id}")
        return

    db.add(
        Enrollment(
            user_id=user_id,
            course_id=course_id,
            progress_percent=0,
        )
    )
    print(f"created enrollment: user={user_id} course={course_id}")


def ensure_pro_test_user(db) -> User:
    user = db.query(User).filter(User.email == PRO_TEST_EMAIL).first()
    if user is None:
        user = User(
            name="Smoke Pro User",
            email=PRO_TEST_EMAIL,
            password_hash=hash_password(PRO_TEST_PASSWORD),
            avatar_url="",
            provider="local",
            onboarding_completed=True,
            current_score=450,
            target_score=750,
            study_minutes_per_day=30,
            weak_skills_json='["grammar"]',
            subscription_plan="pro",
            plan_expired_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(user)
        db.flush()
        print(f"created pro test user: {PRO_TEST_EMAIL}")
    else:
        user.subscription_plan = "pro"
        user.plan_expired_at = datetime.utcnow() + timedelta(days=30)
        user.onboarding_completed = True
        if not user.password_hash:
            user.password_hash = hash_password(PRO_TEST_PASSWORD)
        print(f"updated pro test user: {PRO_TEST_EMAIL}")

    return user


def main() -> None:
    db = SessionLocal()
    try:
        course = ensure_course(db)
        ensure_user_enrollment(db, DEFAULT_USER_ID, course.id)
        pro_user = ensure_pro_test_user(db)
        ensure_user_enrollment(db, pro_user.id, course.id)
        db.commit()
        print("minimal flow seed complete")
        print(f"courseId={course.id}")
        print(f"defaultUserId={DEFAULT_USER_ID}")
        print(f"proTestEmail={PRO_TEST_EMAIL}")
        print(f"proTestPassword={PRO_TEST_PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
