from __future__ import annotations

import json
import logging
import re
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
    ToeicPracticeQuestionOption,
    ToeicPracticeSet,
)


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MANIFESTS_DIR = BACKEND_ROOT / "runtime" / "static" / "toeic" / "manifests"

IMPORT_TARGETS = [
    {
        "manifest": "fulltest_test1_questions.json",
        "code": "fulltest_test1",
        "title": "TOEIC Full Test 1",
        "type": "fulltest",
        "test_number": 1,
        "expected_count": 200,
    },
    {
        "manifest": "minitest_test1_questions.json",
        "code": "minitest_test1",
        "title": "TOEIC Mini Test 1",
        "type": "minitest",
        "test_number": 1,
        "expected_count": 100,
    },
]


def _asset_path(value: Any) -> str | None:
    if isinstance(value, dict):
        nested = value.get("path")
        return str(nested).strip() if nested else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _get_audio_path(item: dict[str, Any]) -> str | None:
    return _asset_path(item.get("audio")) or str(item.get("audioUrl") or "").strip() or None


def _get_image_path(item: dict[str, Any]) -> str | None:
    return _asset_path(item.get("image")) or _asset_path(item.get("graphic"))


def _get_passage(item: dict[str, Any]) -> dict[str, str | None]:
    passage = item.get("passage")
    if isinstance(passage, dict):
        title = str(passage.get("title") or "").strip() or None
        text = str(passage.get("text") or passage.get("passageText") or "").strip() or None
        audio = _asset_path(passage.get("audio"))
        image = _asset_path(passage.get("image"))
        return {"title": title, "text": text, "audio": audio, "image": image}
    if isinstance(passage, str) and passage.strip():
        return {"title": None, "text": passage.strip(), "audio": None, "image": None}
    return {"title": None, "text": None, "audio": None, "image": None}


def _resolve_correct_key(item: dict[str, Any]) -> str | None:
    correct_answer = str(item.get("correctAnswer") or "").strip().upper()
    if re.fullmatch(r"[A-Z]", correct_answer):
        return correct_answer
    index = item.get("correctAnswerIndex")
    if isinstance(index, int) and 0 <= index < 26:
        return chr(ord("A") + index)
    return correct_answer[:10] or None


def _build_fallback_group_code(part: int, passage_text: str | None, audio_path: str | None, image_path: str | None) -> str:
    raw = "|".join([str(part), passage_text or "", audio_path or "", image_path or ""])
    digest = sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"part{part}-group-{digest}"


def _should_create_passage(part: int, group_code: str | None, passage_text: str | None, audio_path: str | None, image_path: str | None) -> bool:
    if passage_text:
        return True
    if part in {3, 4, 6, 7} and (group_code or audio_path or image_path):
        return True
    return False


def _delete_existing_target_sets(db: Session, set_type: str, test_number: int) -> None:
    sets = (
        db.query(ToeicPracticeSet)
        .filter(ToeicPracticeSet.type == set_type, ToeicPracticeSet.test_number == test_number)
        .all()
    )
    if not sets:
        return

    for practice_set in sets:
        question_ids = [
            row.id
            for row in db.query(ToeicPracticeQuestion.id)
            .filter(ToeicPracticeQuestion.set_id == practice_set.id)
            .all()
        ]
        passage_ids = [
            row.id
            for row in db.query(ToeicPracticePassage.id)
            .filter(ToeicPracticePassage.set_id == practice_set.id)
            .all()
        ]

        if question_ids:
            db.query(ToeicPracticeQuestionAsset).filter(
                ToeicPracticeQuestionAsset.question_id.in_(question_ids)
            ).delete(synchronize_session=False)
        if passage_ids:
            db.query(ToeicPracticeQuestionAsset).filter(
                ToeicPracticeQuestionAsset.passage_id.in_(passage_ids)
            ).delete(synchronize_session=False)
        if question_ids:
            db.query(ToeicPracticeQuestionOption).filter(
                ToeicPracticeQuestionOption.question_id.in_(question_ids)
            ).delete(synchronize_session=False)
            db.query(ToeicPracticeQuestion).filter(
                ToeicPracticeQuestion.id.in_(question_ids)
            ).delete(synchronize_session=False)
        if passage_ids:
            db.query(ToeicPracticePassage).filter(
                ToeicPracticePassage.id.in_(passage_ids)
            ).delete(synchronize_session=False)

        db.delete(practice_set)
        logger.info("Deleted existing %s test=%s set id=%s.", set_type, test_number, practice_set.id)
    db.flush()


def _add_question_assets(
    db: Session,
    question: ToeicPracticeQuestion,
    audio_path: str | None,
    image_path: str | None,
) -> None:
    for asset_type, path in (("audio", audio_path), ("image", image_path)):
        if path:
            db.add(
                ToeicPracticeQuestionAsset(
                    question_id=question.id,
                    asset_type=asset_type,
                    relative_path=path,
                )
            )


def _add_passage_assets(
    db: Session,
    passage: ToeicPracticePassage,
    audio_path: str | None,
    image_path: str | None,
) -> None:
    for asset_type, path in (("audio", audio_path), ("image", image_path)):
        if path:
            db.add(
                ToeicPracticeQuestionAsset(
                    passage_id=passage.id,
                    asset_type=asset_type,
                    relative_path=path,
                )
            )


def import_target(db: Session, target: dict[str, Any]) -> None:
    manifest_path = MANIFESTS_DIR / str(target["manifest"])
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{manifest_path.name} must contain a JSON list.")

    items = [item for item in data if isinstance(item, dict)]
    expected_count = int(target["expected_count"])
    if len(items) != expected_count:
        raise ValueError(f"{manifest_path.name} expected {expected_count} questions, found {len(items)}.")

    set_type = str(target["type"])
    test_number = int(target["test_number"])
    _delete_existing_target_sets(db, set_type, test_number)

    practice_set = ToeicPracticeSet(
        code=str(target["code"]),
        title=str(target["title"]),
        type=set_type,
        test_number=test_number,
        part=None,
        is_active=True,
    )
    db.add(practice_set)
    db.flush()

    passages_by_group: dict[str, ToeicPracticePassage] = {}
    imported_questions = 0
    imported_options = 0

    for sort_order, item in enumerate(items):
        part = int(item.get("part") or 0)
        if part < 1 or part > 7:
            raise ValueError(f"{manifest_path.name} has invalid part at item {sort_order}: {part}")

        passage_payload = _get_passage(item)
        passage_text = passage_payload["text"]
        audio_path = passage_payload["audio"] or _get_audio_path(item)
        image_path = passage_payload["image"] or _get_image_path(item)
        group_code = str(item.get("groupId") or "").strip() or None

        passage = None
        if _should_create_passage(part, group_code, passage_text, audio_path, image_path):
            passage_group_code = group_code or _build_fallback_group_code(part, passage_text, audio_path, image_path)
            passage = passages_by_group.get(passage_group_code)
            if passage is None:
                passage = ToeicPracticePassage(
                    set_id=practice_set.id,
                    part=part,
                    group_code=passage_group_code,
                    passage_text=passage_text,
                    audio_path=audio_path,
                    image_path=image_path,
                )
                db.add(passage)
                db.flush()
                _add_passage_assets(db, passage, audio_path, image_path)
                passages_by_group[passage_group_code] = passage

        correct_key = _resolve_correct_key(item)
        question = ToeicPracticeQuestion(
            set_id=practice_set.id,
            passage_id=passage.id if passage else None,
            test_number=int(item.get("test") or test_number),
            part=part,
            section=str(item.get("section") or ("Listening" if part <= 4 else "Reading")),
            question_number=int(item.get("questionNumber") or sort_order + 1),
            question_text=str(item.get("question") or ""),
            correct_option_key=correct_key,
            explanation=item.get("explanation"),
            difficulty=item.get("difficulty") or "mixed",
            skill_code=item.get("skill"),
            sort_order=sort_order,
            is_active=True,
        )
        db.add(question)
        db.flush()

        if passage is None:
            _add_question_assets(db, question, _get_audio_path(item), _get_image_path(item))

        options = item.get("options") or []
        for option_index, option_text in enumerate(options):
            option_key = chr(ord("A") + option_index)
            db.add(
                ToeicPracticeQuestionOption(
                    question_id=question.id,
                    option_key=option_key,
                    option_text=str(option_text or ""),
                    sort_order=option_index,
                    is_correct=option_key == correct_key,
                )
            )
            imported_options += 1

        imported_questions += 1

    db.commit()
    logger.info(
        "Imported %s questions, %s options, %s passages into %s test=%s.",
        imported_questions,
        imported_options,
        len(passages_by_group),
        set_type,
        test_number,
    )


def main() -> None:
    db = SessionLocal()
    try:
        for target in IMPORT_TARGETS:
            import_target(db, target)
        logger.info("Full/mini TOEIC runtime import complete. Existing practice sets were not touched.")
    except Exception:
        db.rollback()
        logger.exception("Full/mini TOEIC runtime import failed.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
