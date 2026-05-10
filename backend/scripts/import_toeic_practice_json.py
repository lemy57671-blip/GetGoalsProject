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


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MANIFESTS_DIR = Path("runtime/static/toeic/manifests")


def _extract_test_number(file_stem: str, items: list[dict[str, Any]]) -> int | None:
    matched = re.search(r"test(\d+)", file_stem, re.IGNORECASE)
    if matched:
        return int(matched.group(1))
    for item in items:
        value = item.get("test")
        if isinstance(value, int) and value > 0:
            return value
    return None


def _resolve_set_info(file_path: Path, items: list[dict[str, Any]]) -> tuple[str, str, str, int | None, int | None]:
    file_stem = file_path.stem
    test_number = _extract_test_number(file_stem, items)
    if file_stem.startswith("part"):
        part_num = int(file_stem.replace("part", "").replace("_questions", ""))
        return "practice", f"practice_part{part_num}", f"Practice Part {part_num}", None, part_num
    if "fulltest" in file_stem:
        return "fulltest", file_stem, f"Full Test {test_number or 1}", test_number, None
    if "minitest" in file_stem:
        return "minitest", file_stem, f"Mini Test {test_number or 1}", test_number, None
    return "practice", file_stem, file_stem, test_number, None


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


def _build_passage_group_code(part: int, passage_text: str | None, audio_path: str | None, image_path: str | None) -> str | None:
    raw = "|".join([str(part), passage_text or "", audio_path or "", image_path or ""]).strip("|")
    if not raw:
        return None
    digest = sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"part{part}-passage-{digest}"


def _resolve_correct_key(item: dict[str, Any]) -> str | None:
    correct_answer = str(item.get("correctAnswer") or "").strip()
    if re.fullmatch(r"[A-Z]", correct_answer.upper()):
        return correct_answer.upper()
    index = item.get("correctAnswerIndex")
    if isinstance(index, int) and 0 <= index < 26:
        return chr(ord("A") + index)
    return correct_answer[:10] or None


def _clear_existing_set(db: Session, practice_set: ToeicPracticeSet) -> None:
    questions = db.query(ToeicPracticeQuestion).filter(ToeicPracticeQuestion.set_id == practice_set.id).all()
    question_ids = [item.id for item in questions]
    passages = db.query(ToeicPracticePassage).filter(ToeicPracticePassage.set_id == practice_set.id).all()
    passage_ids = [item.id for item in passages]

    if question_ids:
        db.query(ToeicPracticeQuestionAsset).filter(ToeicPracticeQuestionAsset.question_id.in_(question_ids)).delete(synchronize_session=False)
        db.query(ToeicPracticeQuestionOption).filter(ToeicPracticeQuestionOption.question_id.in_(question_ids)).delete(synchronize_session=False)
        db.query(ToeicPracticeQuestion).filter(ToeicPracticeQuestion.id.in_(question_ids)).delete(synchronize_session=False)
    if passage_ids:
        db.query(ToeicPracticeQuestionAsset).filter(ToeicPracticeQuestionAsset.passage_id.in_(passage_ids)).delete(synchronize_session=False)
        db.query(ToeicPracticePassage).filter(ToeicPracticePassage.id.in_(passage_ids)).delete(synchronize_session=False)
    db.flush()


def _get_or_create_set(
    db: Session,
    code: str,
    title: str,
    set_type: str,
    test_number: int | None,
    part: int | None,
) -> ToeicPracticeSet:
    practice_set = db.query(ToeicPracticeSet).filter(ToeicPracticeSet.code == code).first()
    if practice_set is None:
        practice_set = ToeicPracticeSet(
            code=code,
            title=title,
            type=set_type,
            test_number=test_number,
            part=part,
            is_active=True,
        )
        db.add(practice_set)
        db.flush()
        return practice_set

    practice_set.title = title
    practice_set.type = set_type
    practice_set.test_number = test_number
    practice_set.part = part
    practice_set.is_active = True
    _clear_existing_set(db, practice_set)
    return practice_set


def _add_passage_assets(db: Session, passage: ToeicPracticePassage) -> None:
    if passage.audio_path:
        db.add(
            ToeicPracticeQuestionAsset(
                passage_id=passage.id,
                asset_type="audio",
                relative_path=passage.audio_path,
            )
        )
    if passage.image_path:
        db.add(
            ToeicPracticeQuestionAsset(
                passage_id=passage.id,
                asset_type="image",
                relative_path=passage.image_path,
            )
        )


def _add_question_assets(db: Session, question: ToeicPracticeQuestion, audio_path: str | None, image_path: str | None) -> None:
    seen: set[tuple[str, str]] = set()
    for asset_type, path in (("audio", audio_path), ("image", image_path)):
        if not path:
            continue
        key = (asset_type, path)
        if key in seen:
            continue
        seen.add(key)
        db.add(
            ToeicPracticeQuestionAsset(
                question_id=question.id,
                asset_type=asset_type,
                relative_path=path,
            )
        )


def import_json_file(db: Session, file_path: Path) -> None:
    logger.info("Importing %s into ToeicPractice runtime tables...", file_path.name)
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        logger.warning("Skipping %s: not a list", file_path.name)
        return

    items = [item for item in data if isinstance(item, dict)]
    set_type, set_code, set_title, set_test_number, set_part = _resolve_set_info(file_path, items)
    practice_set = _get_or_create_set(db, set_code, set_title, set_type, set_test_number, set_part)
    passages_by_group: dict[str, int] = {}

    for index, item in enumerate(items):
        part = int(item.get("part") or set_part or 0)
        passage_text = _get_passage_text(item)
        passage_audio = _get_audio_path(item)
        passage_image = _get_image_path(item)
        group_code = str(item.get("groupId") or "").strip() or None
        passage_group_code = group_code or _build_passage_group_code(part, passage_text, passage_audio, passage_image)
        passage_id = None

        if passage_group_code and (passage_text or passage_audio or passage_image):
            passage_id = passages_by_group.get(passage_group_code)
            if passage_id is None and (passage_text or passage_audio or passage_image):
                passage = ToeicPracticePassage(
                    set_id=practice_set.id,
                    part=part,
                    group_code=passage_group_code,
                    passage_text=passage_text,
                    audio_path=passage_audio,
                    image_path=passage_image,
                )
                db.add(passage)
                db.flush()
                _add_passage_assets(db, passage)
                passages_by_group[passage_group_code] = passage.id
                passage_id = passage.id

        question_audio = _get_audio_path(item) if passage_id is None else None
        question_image = _get_image_path(item) if passage_id is None else None
        question = ToeicPracticeQuestion(
            set_id=practice_set.id,
            passage_id=passage_id,
            test_number=int(item.get("test") or set_test_number or 0) or None,
            part=part,
            section=str(item.get("section") or ("Listening" if part <= 4 else "Reading")),
            question_number=int(item.get("questionNumber") or index + 1),
            question_text=str(item.get("question") or ""),
            correct_option_key=_resolve_correct_key(item),
            explanation=item.get("explanation"),
            difficulty=item.get("difficulty") or "mixed",
            skill_code=item.get("skill"),
            sort_order=index,
            is_active=True,
        )
        db.add(question)
        db.flush()
        _add_question_assets(db, question, question_audio, question_image)

        options = item.get("options") or []
        correct_key = question.correct_option_key
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

    db.commit()
    logger.info("Imported %s runtime questions from %s.", len(items), file_path.name)


def main() -> None:
    db = SessionLocal()
    try:
        if not MANIFESTS_DIR.exists():
            logger.error("Manifests directory not found: %s", MANIFESTS_DIR)
            return
        json_files = sorted(path for path in MANIFESTS_DIR.glob("*.json") if "rejected" not in path.name.lower())
        logger.info("Found %s manifest files.", len(json_files))
        for file_path in json_files:
            import_json_file(db, file_path)
        logger.info("ToeicPractice runtime import complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
