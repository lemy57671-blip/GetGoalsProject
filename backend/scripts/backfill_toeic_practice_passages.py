from __future__ import annotations

import json
import logging
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models import (
    ToeicPracticePassage,
    ToeicPracticeQuestion,
    ToeicPracticeQuestionAsset,
    ToeicPracticeSet,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MANIFESTS_DIR = Path("runtime/static/toeic/manifests")
TARGET_MANIFESTS = ("part6_questions.json", "part7_questions.json")


def _get_asset_path(item: dict[str, Any], key: str) -> str | None:
    raw = item.get(key)
    if isinstance(raw, dict):
        value = raw.get("path")
        return str(value).strip() if value else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _get_audio_path(item: dict[str, Any]) -> str | None:
    return _get_asset_path(item, "audio") or str(item.get("audioUrl") or "").strip() or None


def _get_image_path(item: dict[str, Any]) -> str | None:
    return _get_asset_path(item, "image") or _get_asset_path(item, "graphic")


def _get_passage_text(item: dict[str, Any]) -> str | None:
    passage = item.get("passage")
    if isinstance(passage, dict):
        value = passage.get("text")
        return str(value).strip() if value else None
    if isinstance(passage, str) and passage.strip():
        return passage.strip()
    return None


def _build_group_code(part: int, passage_text: str | None, audio_path: str | None, image_path: str | None) -> str | None:
    raw = "|".join([str(part), passage_text or "", audio_path or "", image_path or ""]).strip("|")
    if not raw:
        return None
    return f"part{part}-passage-{sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _get_or_create_passage(
    db: Session,
    practice_set: ToeicPracticeSet,
    part: int,
    group_code: str,
    passage_text: str | None,
    audio_path: str | None,
    image_path: str | None,
) -> ToeicPracticePassage:
    passage = (
        db.query(ToeicPracticePassage)
        .filter(
            ToeicPracticePassage.set_id == practice_set.id,
            ToeicPracticePassage.part == part,
            ToeicPracticePassage.group_code == group_code,
        )
        .first()
    )
    if passage is None:
        passage = ToeicPracticePassage(
            set_id=practice_set.id,
            part=part,
            group_code=group_code,
            passage_text=passage_text,
            audio_path=audio_path,
            image_path=image_path,
        )
        db.add(passage)
        db.flush()
    else:
        passage.passage_text = passage.passage_text or passage_text
        passage.audio_path = passage.audio_path or audio_path
        passage.image_path = passage.image_path or image_path

    _ensure_passage_asset(db, passage, "audio", audio_path)
    _ensure_passage_asset(db, passage, "image", image_path)
    return passage


def _ensure_passage_asset(db: Session, passage: ToeicPracticePassage, asset_type: str, path: str | None) -> None:
    if not path:
        return
    exists = (
        db.query(ToeicPracticeQuestionAsset.id)
        .filter(
            ToeicPracticeQuestionAsset.passage_id == passage.id,
            ToeicPracticeQuestionAsset.asset_type == asset_type,
            ToeicPracticeQuestionAsset.relative_path == path,
        )
        .first()
    )
    if exists:
        return
    db.add(
        ToeicPracticeQuestionAsset(
            passage_id=passage.id,
            asset_type=asset_type,
            relative_path=path,
        )
    )


def _find_question(db: Session, practice_set: ToeicPracticeSet, item: dict[str, Any], part: int) -> ToeicPracticeQuestion | None:
    test_number = int(item.get("test") or 0) or None
    question_number = int(item.get("questionNumber") or 0) or None
    question_text = str(item.get("question") or "")
    query = db.query(ToeicPracticeQuestion).filter(
        ToeicPracticeQuestion.set_id == practice_set.id,
        ToeicPracticeQuestion.part == part,
        ToeicPracticeQuestion.question_number == question_number,
    )
    if test_number is None:
        query = query.filter(ToeicPracticeQuestion.test_number.is_(None))
    else:
        query = query.filter(ToeicPracticeQuestion.test_number == test_number)

    question = query.filter(ToeicPracticeQuestion.question_text == question_text).first()
    return question or query.first()


def backfill_manifest(db: Session, manifest_path: Path) -> tuple[int, int]:
    with manifest_path.open("r", encoding="utf-8") as f:
        raw_items = json.load(f)
    items = [item for item in raw_items if isinstance(item, dict)]
    if not items:
        return 0, 0

    part = int(items[0].get("part") or 0)
    practice_set = db.query(ToeicPracticeSet).filter(ToeicPracticeSet.code == f"practice_part{part}").first()
    if practice_set is None:
        logger.warning("Skipping %s: practice set for Part %s was not found.", manifest_path.name, part)
        return 0, 0

    updated = 0
    created_or_reused = 0
    for item in items:
        passage_text = _get_passage_text(item)
        audio_path = _get_audio_path(item)
        image_path = _get_image_path(item)
        group_code = str(item.get("groupId") or "").strip() or _build_group_code(part, passage_text, audio_path, image_path)
        if not group_code or not (passage_text or audio_path or image_path):
            continue

        passage = _get_or_create_passage(db, practice_set, part, group_code, passage_text, audio_path, image_path)
        created_or_reused += 1
        question = _find_question(db, practice_set, item, part)
        if question is not None and question.passage_id != passage.id:
            question.passage_id = passage.id
            updated += 1

    db.flush()
    return updated, created_or_reused


def main() -> None:
    db = SessionLocal()
    try:
        total_updated = 0
        total_passage_hits = 0
        for name in TARGET_MANIFESTS:
            updated, passage_hits = backfill_manifest(db, MANIFESTS_DIR / name)
            total_updated += updated
            total_passage_hits += passage_hits
            logger.info("Backfilled %s: linked %s questions using %s passage references.", name, updated, passage_hits)
        db.commit()
        logger.info("Backfill complete: linked %s questions using %s passage references.", total_updated, total_passage_hits)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
