from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import ReviewQueueItem, ToeicPassage, ToeicQuestion, ToeicQuestionAsset, ToeicSet, User
from app.schemas.roadmap import RoadmapSuggestedSetCriteriaDto
from app.schemas.toeic import (
    ToeicBundleSummaryDto,
    ToeicImportStatusDto,
    ToeicInventoryDto,
    ToeicPartInventoryDto,
    ToeicRecommendationDto,
    ToeicRecommendedPackDto,
    ToeicReviewFocusRunnerDto,
    ToeicRunnerAssetDto,
    ToeicRunnerPassageDto,
    ToeicRunnerQuestionDto,
    ToeicSourceFilesDto,
)
from app.services.skill_analytics import normalize_skill_code, normalize_subskill_code
from app.utils.json_helpers import parse_string_list


SQL_SUMMARY_PATH = "sql://ToeicSets"
LISTENING_SIGNALS = ("listening", "part1", "part2", "part3", "part4", "photograph", "question-response", "conversation", "talk")
READING_SIGNALS = ("reading", "grammar", "vocab", "part5", "part6", "part7", "text completion", "reading comprehension")
FULL_TEST_BLUEPRINT: dict[int, int] = {
    1: 6,
    2: 25,
    3: 39,
    4: 30,
    5: 30,
    6: 16,
    7: 54,
}
FULL_TEST_GROUP_SIZES: dict[int, int] = {
    3: 3,
    4: 3,
    6: 4,
}
FULL_TEST_TOTAL_QUESTIONS = sum(FULL_TEST_BLUEPRINT.values())
# SQL Server data check:
# SELECT PartNumber AS Part, COUNT(*) AS Total
# FROM dbo.ToeicDocxQuestions
# GROUP BY PartNumber
# ORDER BY PartNumber;


class FullToeicTestAvailabilityError(Exception):
    def __init__(self, required: dict[int, int], available: dict[int, int], selected: dict[int, int] | None = None):
        self.required = {str(part): count for part, count in required.items()}
        normalized_available = {part: int(available.get(part, 0)) for part in required}
        if selected:
            normalized_available = {
                part: min(normalized_available.get(part, 0), int(selected.get(part, normalized_available.get(part, 0))))
                for part in required
            }
        self.available = {str(part): normalized_available.get(part, 0) for part in required}
        self.missing = {
            str(part): max(0, required_count - normalized_available.get(part, 0))
            for part, required_count in required.items()
            if required_count > normalized_available.get(part, 0)
        }
        super().__init__("Full TOEIC test requires 200 questions but database is missing questions.")

    def to_payload(self) -> dict[str, Any]:
        return {
            "detail": "Full TOEIC test requires 200 questions but database is missing questions.",
            "required": self.required,
            "available": self.available,
            "missing": self.missing,
        }


def get_import_status(db: Session) -> ToeicImportStatusDto:
    ready = db.scalar(select(ToeicSet.id).where(ToeicSet.is_active).limit(1)) is not None
    return ToeicImportStatusDto(
        ready=ready,
        mode="sql-server",
        summaryPath=SQL_SUMMARY_PATH,
        message="TOEIC question bank is loaded from SQL Server." if ready else "TOEIC question bank has not been imported into SQL Server yet.",
        nextStep="Use /api/toeic/summary and runner endpoints backed by SQL Server." if ready else "Run the TOEIC question bank importer before using runner endpoints.",
    )


def get_bundle_summary(db: Session) -> ToeicBundleSummaryDto | None:
    question_rows = db.execute(
        select(ToeicQuestion.part, ToeicQuestion.test_number, ToeicQuestion.question_number)
        .join(ToeicSet, ToeicSet.id == ToeicQuestion.set_id)
        .where(ToeicQuestion.is_active, ToeicSet.is_active)
    ).all()
    if not question_rows:
        return None

    passage_count = db.scalar(
        select(func.count())
        .select_from(ToeicPassage)
        .join(ToeicSet, ToeicSet.id == ToeicPassage.set_id)
        .where(ToeicSet.is_active)
    ) or 0
    question_audio = db.execute(
        select(ToeicQuestion.part, ToeicQuestionAsset.relative_path)
        .join(ToeicQuestion, ToeicQuestion.id == ToeicQuestionAsset.question_id)
        .join(ToeicSet, ToeicSet.id == ToeicQuestion.set_id)
        .where(ToeicQuestionAsset.asset_type == "audio", ToeicQuestion.is_active, ToeicSet.is_active)
    ).all()
    passage_audio = db.execute(
        select(ToeicPassage.part, ToeicPassage.audio_path)
        .join(ToeicSet, ToeicSet.id == ToeicPassage.set_id)
        .where(ToeicSet.is_active, ToeicPassage.audio_path.is_not(None))
    ).all()

    audio_rows: dict[str, int] = {}
    for part, path in list(question_audio) + list(passage_audio):
        if path and path.lower() not in audio_rows:
            audio_rows[path.lower()] = part

    detected_parts = sorted({row.part for row in question_rows})
    summary = ToeicBundleSummaryDto(
        sourceFiles=ToeicSourceFilesDto(
            docx="Imported from TOEIC manifests",
            audioZip="Static assets preserved in FastAPI runtime static storage",
            mappingCsv="Not required at runtime after SQL import",
        ),
        inventory=ToeicInventoryDto(
            mappingRows=len(question_rows),
            audioFiles=len(audio_rows),
            docxParagraphs=passage_count or 0,
            detectedParts=detected_parts,
        ),
        notes=[
            "Question content is served from SQL Server.",
            "Static audio and image assets are served from the FastAPI runtime-owned static roots.",
            "Roadmap rules JSON remains configuration, not question content.",
        ],
    )

    for part in detected_parts:
        rows = [row for row in question_rows if row.part == part]
        summary.parts.append(
            ToeicPartInventoryDto(
                part=part,
                name=_resolve_part_name(part),
                skill="listening" if part <= 4 else "reading",
                count=len(rows),
                audioCount=sum(1 for value in audio_rows.values() if value == part),
                testsAvailable=sorted({row.test_number for row in rows if row.test_number and row.test_number > 0}),
                sampleQuestionRange="" if not rows else f"{min(row.question_number for row in rows)}-{max(row.question_number for row in rows)}",
                audioReady=any(value == part for value in audio_rows.values()),
            )
        )

    return summary


def build_recommendations(db: Session, user_id: int) -> ToeicRecommendationDto:
    summary = get_bundle_summary(db)
    if summary is None:
        return ToeicRecommendationDto(track="unavailable", reason="TOEIC question bank has not been imported into SQL Server yet.")

    user = db.get(User, user_id)
    if user is None:
        return ToeicRecommendationDto(track="unknown_user", reason=f"User {user_id} was not found.", recommendedPacks=_build_balanced_packs(summary))

    weak_skills = parse_string_list(user.weak_skills_json)
    listening_count = sum(1 for item in weak_skills if _contains_any(item, LISTENING_SIGNALS))
    reading_count = sum(1 for item in weak_skills if _contains_any(item, READING_SIGNALS))
    if listening_count > reading_count:
        track = "listening_recovery"
        reason = "Recent weak skills lean toward listening."
        packs = _build_listening_packs(summary)
    elif reading_count > listening_count:
        track = "reading_recovery"
        reason = "Recent weak skills lean toward reading."
        packs = _build_reading_packs(summary)
    else:
        track = "balanced"
        reason = "Recent weak skills are balanced."
        packs = _build_balanced_packs(summary)

    return ToeicRecommendationDto(
        track=track,
        reason=reason,
        currentScore=user.current_score,
        targetScore=user.target_score,
        weakSkills=weak_skills,
        recommendedPacks=packs,
    )


def get_part_runner_questions(db: Session, part: int, limit: int = 30, difficulty: str | None = None, current_score: int | None = None) -> list[ToeicRunnerQuestionDto]:
    items = _load_runner_questions(db, "practice", None, [part])
    filtered = _filter_questions_by_difficulty(items, _normalize_difficulty(difficulty, current_score))
    return filtered[: limit if limit > 0 else len(filtered)]


def get_mixed_runner_questions(db: Session, parts: Iterable[int] | None, count: int = 30, difficulty: str | None = None, current_score: int | None = None) -> list[ToeicRunnerQuestionDto]:
    selected_parts = sorted({part for part in (parts or []) if 1 <= part <= 7}) or [1]
    filtered = _filter_questions_by_difficulty(_load_runner_questions(db, "practice", None, selected_parts), _normalize_difficulty(difficulty, current_score))
    buckets = {part: deque([item for item in filtered if item.part == part]) for part in selected_parts}
    result: list[ToeicRunnerQuestionDto] = []
    active = [part for part in selected_parts if buckets[part]]
    while len(result) < count and active:
        for part in list(active):
            queue = buckets[part]
            if not queue:
                active.remove(part)
                continue
            result.append(queue.popleft())
            if len(result) >= count:
                break
            if not queue:
                active.remove(part)
    return result


def get_review_focus_runner_questions(db: Session, user_id: int, review_item_id: int, count: int = 15, difficulty: str | None = None) -> ToeicReviewFocusRunnerDto | None:
    item = db.scalar(select(ReviewQueueItem).where(ReviewQueueItem.id == review_item_id, ReviewQueueItem.user_id == user_id))
    if item is None:
        return None

    bank = _load_normalized_practice_bank(db)
    if not bank:
        return []

    source = next((row for row in bank if row.question.id == item.question_id), None)
    source_part = item.part if item.part and 1 <= item.part <= 7 else (source.part if source else None)
    source_skill = source.skillCode if source else normalize_skill_code(item.skill)
    source_subskill = source.subskillCode if source else normalize_subskill_code(None, source_skill)
    normalized_difficulty = _normalize_difficulty(difficulty, None)
    normalized_count = max(1, min(count, 60))

    buckets = [
        ("same_part_skill_subskill_difficulty", normalized_difficulty, [
            row
            for row in bank
            if _matches_review_focus(row, source_part, source_skill, source_subskill, normalized_difficulty, item.question_id)
        ]),
        ("same_part_skill_difficulty", normalized_difficulty, [
            row
            for row in bank
            if _matches_review_focus(row, source_part, source_skill, None, normalized_difficulty, item.question_id)
        ]),
        ("same_part_difficulty", normalized_difficulty, [
            row
            for row in bank
            if _matches_review_focus(row, source_part, None, None, normalized_difficulty, item.question_id)
        ]),
        ("same_part_skill_subskill", "mixed", [
            row
            for row in bank
            if _matches_review_focus(row, source_part, source_skill, source_subskill, "mixed", item.question_id)
        ]),
        ("same_part_skill", "mixed", [
            row
            for row in bank
            if _matches_review_focus(row, source_part, source_skill, None, "mixed", item.question_id)
        ]),
        ("same_part", "mixed", [
            row
            for row in bank
            if _matches_review_focus(row, source_part, None, None, "mixed", item.question_id)
        ]),
    ]

    selected: list[_NormalizedToeicQuestion] = []
    seen: set[str] = set()
    strategies_used: list[str] = []
    used_difficulty = normalized_difficulty
    for strategy, bucket_difficulty, bucket in buckets:
        before_count = len(selected)
        for row in _take_balanced_questions(bucket, normalized_count):
            if len(selected) >= normalized_count:
                break
            if row.uniqueKey in seen:
                continue
            seen.add(row.uniqueKey)
            selected.append(row)
        if len(selected) > before_count:
            strategies_used.append(strategy)
            if len(strategies_used) == 1:
                used_difficulty = bucket_difficulty
        if len(selected) >= normalized_count:
            break

    items = [clone_question(row.question) for row in selected]
    return ToeicReviewFocusRunnerDto(
        items=items,
        matchStrategy=strategies_used[0] if strategies_used else "no_match",
        matchStrategiesUsed=strategies_used,
        sourceQuestionId=item.question_id,
        excludedOriginal=True,
        requestedCount=normalized_count,
        returnedCount=len(items),
        usedPart=source_part,
        usedSkill=source_skill,
        usedSubskill=source_subskill,
        usedDifficulty=used_difficulty,
    )


def get_minitest_runner_questions(db: Session, test: int = 1, parts: Iterable[int] | None = None, count: int | None = None) -> list[ToeicRunnerQuestionDto]:
    selected_parts = sorted({part for part in (parts or []) if 1 <= part <= 7})
    ordered = [clone_question(item) for item in _load_runner_questions(db, "minitest", test, selected_parts or None)]
    return ordered[:count] if count and count > 0 else ordered


def get_fulltest_runner_questions(db: Session, test: int = 1) -> list[ToeicRunnerQuestionDto]:
    return _build_full_test_questions(db, test)


def get_question_lookup(db: Session) -> dict[str, ToeicRunnerQuestionDto]:
    return {
        build_question_lookup_key(row.question.part, row.question.id): clone_question(row.question)
        for row in _load_normalized_practice_bank(db)
    }


def get_question_lookup_by_ids(db: Session, question_ids: Iterable[int]) -> dict[str, ToeicRunnerQuestionDto]:
    ids = sorted({int(value) for value in question_ids if value and int(value) > 0})
    if not ids:
        return {}

    rows = db.scalars(
        select(ToeicQuestion)
        .join(ToeicSet, ToeicSet.id == ToeicQuestion.set_id)
        .options(
            joinedload(ToeicQuestion.set),
            joinedload(ToeicQuestion.passage).selectinload(ToeicPassage.assets),
            selectinload(ToeicQuestion.options),
            selectinload(ToeicQuestion.assets),
        )
        .where(ToeicQuestion.is_active, ToeicSet.is_active, ToeicQuestion.id.in_(ids))
        .order_by(ToeicQuestion.part, ToeicQuestion.test_number, ToeicQuestion.question_number, ToeicQuestion.sort_order)
    ).all()

    return {
        build_question_lookup_key(row.part, row.id): _map_to_runner_question(row)
        for row in rows
    }


def get_runner_questions_by_ids(db: Session, question_ids: Iterable[int]) -> list[ToeicRunnerQuestionDto]:
    ids = []
    for value in question_ids:
        try:
            question_id = int(value)
        except (TypeError, ValueError):
            continue
        if question_id > 0 and question_id not in ids:
            ids.append(question_id)

    if not ids:
        return []

    docx_questions = _load_docx_runner_questions_by_ids(db, ids)
    mapped_docx = {question.id: question for question in docx_questions}
    missing_ids = [question_id for question_id in ids if question_id not in mapped_docx]

    if not missing_ids:
        return [mapped_docx[question_id] for question_id in ids if question_id in mapped_docx]

    rows = db.scalars(
        select(ToeicQuestion)
        .join(ToeicSet, ToeicSet.id == ToeicQuestion.set_id)
        .options(
            joinedload(ToeicQuestion.set),
            joinedload(ToeicQuestion.passage).selectinload(ToeicPassage.assets),
            selectinload(ToeicQuestion.options),
            selectinload(ToeicQuestion.assets),
        )
        .where(ToeicQuestion.is_active, ToeicSet.is_active, ToeicQuestion.id.in_(missing_ids))
    ).all()

    mapped = {row.id: _map_to_runner_question(row) for row in rows}
    return [mapped_docx.get(question_id) or mapped[question_id] for question_id in ids if question_id in mapped_docx or question_id in mapped]


def _build_full_test_questions(db: Session, test: int = 1) -> list[ToeicRunnerQuestionDto]:
    rows = _load_docx_rows_for_full_test(db, test)
    rows_by_part: dict[int, list[dict[str, Any]]] = {part: [] for part in FULL_TEST_BLUEPRINT}
    for row in rows:
        part = _to_int(row.get("PartNumber"))
        if part in rows_by_part:
            rows_by_part[part].append(row)

    available = {part: len(rows_by_part.get(part, [])) for part in FULL_TEST_BLUEPRINT}
    missing_by_count = {
        part: required
        for part, required in FULL_TEST_BLUEPRINT.items()
        if available.get(part, 0) < required
    }
    if missing_by_count:
        raise FullToeicTestAvailabilityError(FULL_TEST_BLUEPRINT, available)

    selected: list[dict[str, Any]] = []
    selected_counts: dict[int, int] = {}
    for part, required in FULL_TEST_BLUEPRINT.items():
        part_rows = sorted(rows_by_part.get(part, []), key=_docx_sort_key)
        group_size = FULL_TEST_GROUP_SIZES.get(part)
        if group_size:
            part_selection = _select_docx_grouped_rows(part_rows, required, group_size)
        else:
            part_selection = part_rows[:required]
        selected_counts[part] = len(part_selection)
        selected.extend(part_selection)

    if len(selected) != FULL_TEST_TOTAL_QUESTIONS or any(selected_counts.get(part, 0) < required for part, required in FULL_TEST_BLUEPRINT.items()):
        raise FullToeicTestAvailabilityError(FULL_TEST_BLUEPRINT, available, selected_counts)

    return _map_docx_rows_to_runner_questions(db, selected)


def _load_docx_rows_for_full_test(db: Session, test: int = 1) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT Id, SourceFile, TestNumber, PartNumber, QuestionNumber, PassageText, QuestionTextEn,
                   CorrectOptionLabel, CorrectAnswerText, ExplanationDetail, OptionAnalysis,
                   VocabularyNotes, FinalTranslationVi, TranslationVi, RawBlock
            FROM dbo.ToeicDocxQuestions
            WHERE TestNumber = :test_number
            ORDER BY PartNumber, QuestionNumber, Id
            """
        ),
        {"test_number": test},
    ).mappings().all()
    return [dict(row) for row in rows]


def _select_docx_grouped_rows(rows: list[dict[str, Any]], required: int, group_size: int) -> list[dict[str, Any]]:
    required_groups = required // group_size
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = _docx_group_key(row)
        if key:
            grouped.setdefault(key, []).append(row)

    complete_groups = [
        sorted(group_rows, key=_docx_sort_key)[:group_size]
        for group_rows in sorted(grouped.values(), key=lambda group: _docx_sort_key(sorted(group, key=_docx_sort_key)[0]))
        if len(group_rows) >= group_size
    ]
    if len(complete_groups) >= required_groups:
        return [row for group in complete_groups[:required_groups] for row in group]

    sorted_rows = sorted(rows, key=_docx_sort_key)
    fallback_groups = [
        sorted_rows[index : index + group_size]
        for index in range(0, len(sorted_rows), group_size)
        if len(sorted_rows[index : index + group_size]) == group_size
    ]
    return [row for group in fallback_groups[:required_groups] for row in group]


def _docx_group_key(row: dict[str, Any]) -> str | None:
    for field in ("PassageText",):
        value = str(row.get(field) or "").strip()
        if value:
            return f"{field}:{sha256(value.encode('utf-8')).hexdigest()}"
    return None


def _docx_sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (
        _to_int(row.get("PartNumber")) or 0,
        _to_int(row.get("QuestionNumber")) or 0,
        _to_int(row.get("Id")) or 0,
    )


def _map_docx_rows_to_runner_questions(db: Session, rows: list[dict[str, Any]]) -> list[ToeicRunnerQuestionDto]:
    if not rows:
        return []
    ids = [_to_int(row.get("Id")) for row in rows]
    ids = [value for value in ids if value > 0]
    options_by_question = _load_docx_options_by_question(db, ids)

    result: list[ToeicRunnerQuestionDto] = []
    for row in rows:
        question_id = _to_int(row.get("Id"))
        if question_id <= 0:
            continue
        part = _to_int(row.get("PartNumber")) or 1
        option_rows = options_by_question.get(question_id, [])
        option_texts = [str(item.get("OptionTextEn") or "") for item in option_rows]
        correct_label = str(row.get("CorrectOptionLabel") or "").strip().upper()
        correct_index = next(
            (
                index
                for index, item in enumerate(option_rows)
                if str(item.get("OptionLabel") or "").strip().upper() == correct_label
                or bool(item.get("IsCorrect"))
            ),
            None,
        )
        correct_answer = str(row.get("CorrectAnswerText") or "").strip() or (
            option_texts[correct_index] if correct_index is not None and correct_index < len(option_texts) else None
        )
        explanation = (
            str(row.get("ExplanationDetail") or "").strip()
            or str(row.get("OptionAnalysis") or "").strip()
            or str(row.get("VocabularyNotes") or "").strip()
            or None
        )
        result.append(
            ToeicRunnerQuestionDto(
                id=question_id,
                questionId=question_id,
                dbId=question_id,
                docxQuestionId=question_id,
                sourceQuestionId=question_id,
                section="Listening" if part <= 4 else "Reading",
                part=part,
                partLabel=f"Part {part}",
                type="fulltest_docx",
                question=str(row.get("QuestionTextEn") or ""),
                skill="TOEIC full test",
                subskill=None,
                groupId=_docx_group_key(row),
                test=_to_int(row.get("TestNumber")) or 0,
                questionNumber=_to_int(row.get("QuestionNumber")) or 0,
                options=option_texts,
                correctAnswer=correct_answer,
                correctAnswerIndex=correct_index,
                explanation=explanation,
                difficulty="mixed",
                passage=ToeicRunnerPassageDto(title="", text=str(row.get("PassageText") or "")),
            )
        )
    return result


def _load_docx_options_by_question(db: Session, question_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not question_ids:
        return {}
    ids_csv = ",".join(str(value) for value in question_ids)
    option_rows = db.execute(
        text(
            """
            SELECT QuestionId, OptionLabel, OptionTextEn, IsCorrect, SortOrder
            FROM dbo.ToeicDocxOptions
            WHERE QuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:ids_csv, ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            ORDER BY QuestionId, SortOrder
            """
        ),
        {"ids_csv": ids_csv},
    ).mappings().all()
    result: dict[int, list[dict[str, Any]]] = {}
    for row in option_rows:
        data = dict(row)
        result.setdefault(_to_int(data.get("QuestionId")), []).append(data)
    return result


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _load_docx_runner_questions_by_ids(db: Session, question_ids: list[int]) -> list[ToeicRunnerQuestionDto]:
    if not question_ids:
        return []

    ids_csv = ",".join(str(value) for value in question_ids)
    question_rows = db.execute(
        text(
            """
            SELECT Id, TestNumber, PartNumber, QuestionNumber, PassageText, QuestionTextEn,
                   CorrectOptionLabel, CorrectAnswerText, ExplanationDetail, OptionAnalysis,
                   VocabularyNotes, FinalTranslationVi, TranslationVi
            FROM dbo.ToeicDocxQuestions
            WHERE Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:ids_csv, ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ids_csv},
    ).all()

    option_rows = db.execute(
        text(
            """
            SELECT QuestionId, OptionLabel, OptionTextEn, IsCorrect, SortOrder
            FROM dbo.ToeicDocxOptions
            WHERE QuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:ids_csv, ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            ORDER BY QuestionId, SortOrder
            """
        ),
        {"ids_csv": ids_csv},
    ).all()

    options_by_question: dict[int, list[dict]] = {}
    for row in option_rows:
        data = dict(row._mapping)
        options_by_question.setdefault(int(data["QuestionId"]), []).append(data)

    mapped: dict[int, ToeicRunnerQuestionDto] = {}
    for row in question_rows:
        data = dict(row._mapping)
        question_id = int(data["Id"])
        options = options_by_question.get(question_id, [])
        option_texts = [str(item.get("OptionTextEn") or "") for item in options]
        correct_label = str(data.get("CorrectOptionLabel") or "").strip().upper()
        correct_index = next(
            (
                index
                for index, item in enumerate(options)
                if str(item.get("OptionLabel") or "").strip().upper() == correct_label
                or bool(item.get("IsCorrect"))
            ),
            None,
        )
        correct_answer = str(data.get("CorrectAnswerText") or "").strip() or (
            option_texts[correct_index] if correct_index is not None and correct_index < len(option_texts) else None
        )
        part = int(data.get("PartNumber") or 1)
        explanation = (
            str(data.get("ExplanationDetail") or "").strip()
            or str(data.get("OptionAnalysis") or "").strip()
            or str(data.get("VocabularyNotes") or "").strip()
            or None
        )
        mapped[question_id] = ToeicRunnerQuestionDto(
            id=question_id,
            questionId=question_id,
            dbId=question_id,
            docxQuestionId=question_id,
            sourceQuestionId=question_id,
            section="Listening" if part <= 4 else "Reading",
            part=part,
            partLabel=f"Part {part}",
            type="docx_review",
            question=str(data.get("QuestionTextEn") or ""),
            skill="TOEIC review",
            subskill=None,
            test=int(data.get("TestNumber") or 0),
            questionNumber=int(data.get("QuestionNumber") or 0),
            options=option_texts,
            correctAnswer=correct_answer,
            correctAnswerIndex=correct_index,
            explanation=explanation,
            difficulty="mixed",
            passage=ToeicRunnerPassageDto(title="", text=str(data.get("PassageText") or "")),
        )

    return [mapped[question_id] for question_id in question_ids if question_id in mapped]


def build_question_lookup_key(part: int, question_id: int) -> str:
    return f"{part}:{question_id}"


def build_suggested_weekly_sets(focus_skill: str, focus_part: int | None, subskills: Iterable[str] | None, difficulty: str = "mixed", question_count: int = 30) -> list[RoadmapSuggestedSetCriteriaDto]:
    normalized_subskills = []
    for item in subskills or []:
        value = item.strip()
        if value and value.lower() not in {existing.lower() for existing in normalized_subskills}:
            normalized_subskills.append(value)
    include_parts = _resolve_parts_for_skill(focus_skill, focus_part)
    return [
        RoadmapSuggestedSetCriteriaDto(strategy="focus", focusSkill=focus_skill, focusPart=focus_part, includeParts=include_parts, subskills=normalized_subskills[:2], difficulty=difficulty, questionCount=question_count, tags=["focus", "weekly"]),
        RoadmapSuggestedSetCriteriaDto(strategy="subskill_mix", focusSkill=focus_skill, focusPart=focus_part, includeParts=include_parts, subskills=normalized_subskills, difficulty=difficulty, questionCount=question_count, tags=["subskills", "targeted"]),
        RoadmapSuggestedSetCriteriaDto(strategy="mixed_review", focusSkill=focus_skill, focusPart=focus_part, includeParts=include_parts, subskills=normalized_subskills, difficulty="mixed", questionCount=question_count, tags=["mixed", "review"]),
    ]


def get_questions_for_suggested_set(db: Session, criteria: RoadmapSuggestedSetCriteriaDto) -> list[ToeicRunnerQuestionDto]:
    bank = _load_normalized_practice_bank(db)
    if not bank:
        return []
    count = max(10, min(criteria.questionCount, 60))
    difficulty = _normalize_difficulty(criteria.difficulty, None)
    parts = _resolve_parts_for_criteria(criteria)
    focus_skill = (criteria.focusSkill or "").strip()
    subskills = [item.strip() for item in criteria.subskills if item.strip()]

    buckets = [
        [item for item in bank if _matches_parts(item, parts) and _matches_difficulty(item, difficulty) and _matches_skill(item, focus_skill) and _matches_subskills(item, subskills)],
        [item for item in bank if _matches_parts(item, parts) and _matches_skill(item, focus_skill) and _matches_subskills(item, subskills)],
        [item for item in bank if _matches_parts(item, parts) and _matches_difficulty(item, difficulty) and _matches_skill(item, focus_skill)],
        [item for item in bank if _matches_parts(item, parts) and _matches_skill(item, focus_skill)],
        [item for item in bank if _matches_parts(item, parts) and _matches_difficulty(item, difficulty)],
        [item for item in bank if _matches_parts(item, parts)],
        [item for item in bank if _matches_skill(item, focus_skill)],
        bank,
    ]

    selected: list[_NormalizedToeicQuestion] = []
    seen: set[str] = set()
    for bucket in buckets:
        for item in _take_balanced_questions(bucket, count):
            if len(selected) >= count:
                break
            if item.uniqueKey in seen:
                continue
            seen.add(item.uniqueKey)
            selected.append(item)
        if len(selected) >= count:
            break

    return [clone_question(item.question) for item in sorted(selected, key=lambda x: (x.question.part, x.question.test, x.question.questionNumber))[:count]]


def _load_runner_questions(db: Session, set_type: str, set_test_number: int | None, parts: list[int] | None) -> list[ToeicRunnerQuestionDto]:
    query = (
        select(ToeicQuestion)
        .join(ToeicSet, ToeicSet.id == ToeicQuestion.set_id)
        .options(
            joinedload(ToeicQuestion.set),
            joinedload(ToeicQuestion.passage).selectinload(ToeicPassage.assets),
            selectinload(ToeicQuestion.options),
            selectinload(ToeicQuestion.assets),
        )
        .where(ToeicQuestion.is_active, ToeicSet.is_active, ToeicSet.type == set_type)
        .order_by(ToeicQuestion.part, ToeicQuestion.test_number, ToeicQuestion.question_number, ToeicQuestion.sort_order)
    )
    if set_test_number is not None:
        query = query.where(ToeicSet.test_number == set_test_number)
    if parts:
        query = query.where(ToeicQuestion.part.in_(parts))
    rows = db.scalars(query).all()
    docx_lookup = _load_docx_question_id_lookup(db, rows)
    return [_map_to_runner_question(row, docx_lookup.get(row.id)) for row in rows]


def _load_docx_question_id_lookup(db: Session, questions: list[ToeicQuestion]) -> dict[int, int]:
    lookup: dict[int, int] = {}
    if not questions:
        return lookup
    for question in questions:
        try:
            row = db.execute(
                text(
                    """
                    SELECT TOP 1 Id
                    FROM dbo.ToeicDocxQuestions
                    WHERE QuestionNumber = :question_number
                      AND PartNumber = :part
                      AND (:test_number IS NULL OR TestNumber = :test_number)
                      AND QuestionTextEn = :question_text
                    ORDER BY Id
                    """
                ),
                {
                    "question_number": question.question_number,
                    "part": question.part,
                    "test_number": question.test_number,
                    "question_text": question.question_text,
                },
            ).mappings().first()
            if row and row.get("Id"):
                lookup[question.id] = int(row.get("Id"))
        except Exception:
            return lookup
    return lookup


def _map_to_runner_question(question: ToeicQuestion, docx_question_id: int | None = None) -> ToeicRunnerQuestionDto:
    audio_path = _resolve_asset_path(question, "audio") or question.audio_url
    graphic_path = _resolve_asset_path(question, "graphic")
    image_path = _resolve_asset_path(question, "image")
    options = sorted(question.options, key=lambda item: (item.sort_order, item.option_key))
    return ToeicRunnerQuestionDto(
        id=question.id,
        questionId=docx_question_id or question.id,
        dbId=docx_question_id,
        docxQuestionId=docx_question_id,
        sourceQuestionId=docx_question_id,
        section=question.section or _infer_section(question.part),
        part=question.part,
        partLabel=question.part_label or f"Part {question.part}",
        type=question.question_type or "question",
        question=question.question_text,
        skill=question.topic or question.skill_code or "",
        subskill=question.subskill_code,
        groupId=question.group_code or (question.passage.group_code if question.passage else None),
        test=question.test_number,
        questionNumber=question.question_number,
        options=[item.option_text for item in options],
        correctAnswer=question.correct_option_key or None,
        correctAnswerIndex=_resolve_option_index(question.correct_option_key),
        explanation=question.explanation,
        difficulty=question.difficulty or "mixed",
        abilityBand=question.ability_band or "intermediate",
        minScore=question.min_score,
        maxScore=question.max_score,
        image=ToeicRunnerAssetDto(path=image_path) if image_path else None,
        graphic=ToeicRunnerAssetDto(path=graphic_path) if graphic_path else None,
        audio=ToeicRunnerAssetDto(path=audio_path) if audio_path else None,
        audioUrl=audio_path,
        passage=ToeicRunnerPassageDto(title=question.passage.title or "", text=question.passage.passage_text or "") if question.passage and ((question.passage.title or "").strip() or (question.passage.passage_text or "").strip()) else None,
    )


def _resolve_asset_path(question: ToeicQuestion, asset_type: str) -> str | None:
    question_asset = next((item.relative_path for item in sorted(question.assets, key=lambda x: x.sort_order) if item.asset_type.lower() == asset_type.lower() and item.relative_path), None)
    if question_asset:
        return question_asset
    if question.passage:
        passage_asset = next((item.relative_path for item in sorted(question.passage.assets, key=lambda x: x.sort_order) if item.asset_type.lower() == asset_type.lower() and item.relative_path), None)
        if passage_asset:
            return passage_asset
        if asset_type == "audio":
            return question.passage.audio_path or question.audio_url
        if asset_type in {"graphic", "image"}:
            return question.passage.image_path
    return question.audio_url if asset_type == "audio" else None


def _load_normalized_practice_bank(db: Session) -> list["_NormalizedToeicQuestion"]:
    return [_normalize_question(item) for item in _load_runner_questions(db, "practice", None, None)]


def _normalize_question(question: ToeicRunnerQuestionDto) -> "_NormalizedToeicQuestion":
    copy = clone_question(question)
    skill_code = _normalize_manifest_skill(copy)
    subskill_code = _normalize_manifest_subskill(copy, skill_code)
    copy.subskill = subskill_code
    return _NormalizedToeicQuestion(
        uniqueKey=f"{copy.part}:{copy.test}:{copy.questionNumber}:{copy.id}",
        question=copy,
        skillCode=skill_code,
        subskillCode=subskill_code,
        difficulty=_normalize_difficulty(copy.difficulty, copy.maxScore),
        part=copy.part,
    )


def clone_question(question: ToeicRunnerQuestionDto) -> ToeicRunnerQuestionDto:
    return ToeicRunnerQuestionDto.model_validate(question.model_dump())


def _normalize_manifest_skill(question: ToeicRunnerQuestionDto) -> str:
    raw_skill = (question.skill or "").strip().lower()
    prompt = (question.question or "").strip().lower()
    if question.part == 1:
        return "listening_detail"
    if question.part == 2:
        return "listening_response"
    if question.part == 3:
        if any(token in prompt for token in ("mainly", "purpose", "main idea")):
            return "listening_main_idea"
        if any(token in prompt for token in ("imply", "suggest", "why")):
            return "listening_inference"
        return "listening_detail"
    if question.part == 4:
        if any(token in prompt for token in ("mainly", "purpose", "main idea")):
            return "listening_main_idea"
        if any(token in prompt for token in ("imply", "suggest", "why")):
            return "listening_inference"
        return "listening_detail"
    if question.part == 5 and "vocab" in raw_skill and "grammar" not in raw_skill:
        return "vocabulary"
    if question.part == 5:
        return "grammar"
    if question.part == 6:
        return "reading_context"
    if question.part == 7 and any(token in prompt for token in ("imply", "suggest", "inferred")):
        return "reading_inference"
    if question.part == 7:
        return "reading_detail"
    return normalize_skill_code(question.skill, question.subskill)


def _normalize_manifest_subskill(question: ToeicRunnerQuestionDto, normalized_skill: str) -> str:
    prompt = (question.question or "").strip().lower()
    raw_skill = (question.skill or "").strip().lower()
    if question.part == 1:
        return "object_location" if "location" in prompt or "location" in raw_skill else "identifying_actions"
    if question.part == 2:
        return "question_response"
    if question.part == 3:
        if "mainly" in prompt or "purpose" in prompt:
            return "main_idea"
        if "imply" in prompt or "suggest" in prompt:
            return "speaker_intent"
        return "specific_information"
    if question.part == 4:
        if "graphic" in prompt:
            return "graphic_reference"
        if "purpose" in prompt:
            return "purpose"
        if "next" in prompt or "do next" in prompt:
            return "next_step"
        if "mainly" in prompt or "about" in prompt:
            return "speaker_context"
        return "specific_information"
    if question.part == 5:
        return "business_vocabulary" if "vocab" in raw_skill and "grammar" not in raw_skill else "grammar_foundation"
    if question.part == 6:
        return "sentence_insertion" if "insert" in prompt else "reading_context"
    if question.part == 7:
        if "imply" in prompt or "suggest" in prompt:
            return "implied_meaning"
        if "purpose" in prompt:
            return "main_idea"
        return "scanning"
    return normalize_subskill_code(question.subskill, normalized_skill)


def _contains_any(value: str, signals: Iterable[str]) -> bool:
    lower = value.strip().lower()
    return any(signal.lower() in lower for signal in signals)


def _resolve_option_index(option_key: str | None) -> int | None:
    if not option_key:
        return None
    first = option_key.strip().upper()[0]
    return ord(first) - ord("A") if "A" <= first <= "Z" else None


def _normalize_difficulty(difficulty: str | None, current_score: int | None) -> str:
    if difficulty and difficulty.strip().lower() in {"easy", "medium", "hard", "mixed"}:
        return difficulty.strip().lower()
    if current_score is None:
        return "mixed"
    if current_score <= 450:
        return "easy"
    if current_score <= 750:
        return "medium"
    return "hard"


def _filter_questions_by_difficulty(questions: list[ToeicRunnerQuestionDto], difficulty: str) -> list[ToeicRunnerQuestionDto]:
    if difficulty == "mixed":
        return questions
    by_difficulty = [item for item in questions if (item.difficulty or "").lower() == difficulty]
    if by_difficulty:
        return by_difficulty
    if difficulty == "easy":
        by_score_band = [item for item in questions if item.maxScore is not None and item.maxScore <= 450]
    elif difficulty == "medium":
        by_score_band = [item for item in questions if item.minScore is not None and item.maxScore is not None and item.minScore <= 750 and item.maxScore >= 451]
    else:
        by_score_band = [item for item in questions if item.minScore is not None and item.minScore >= 751]
    return by_score_band or questions


def _resolve_parts_for_criteria(criteria: RoadmapSuggestedSetCriteriaDto) -> list[int]:
    if criteria.includeParts:
        return sorted({part for part in criteria.includeParts if 1 <= part <= 7})
    return _resolve_parts_for_skill(criteria.focusSkill, criteria.focusPart)


def _resolve_parts_for_skill(focus_skill: str | None, focus_part: int | None) -> list[int]:
    if focus_part and 1 <= focus_part <= 7:
        return [focus_part]
    return {
        "listening_response": [2],
        "listening_inference": [3, 4],
        "listening_main_idea": [3, 4],
        "listening_detail": [1, 3, 4],
        "grammar": [5],
        "vocabulary": [5, 6],
        "reading_context": [6],
        "reading_detail": [7],
        "reading_inference": [7],
    }.get((focus_skill or "").strip().lower(), [1, 2, 3, 4, 5, 6, 7])


def _matches_parts(question: "_NormalizedToeicQuestion", parts: list[int]) -> bool:
    return not parts or question.part in parts


def _matches_difficulty(question: "_NormalizedToeicQuestion", difficulty: str) -> bool:
    return difficulty == "mixed" or question.difficulty.lower() == difficulty.lower()


def _matches_skill(question: "_NormalizedToeicQuestion", focus_skill: str) -> bool:
    return not focus_skill or question.skillCode.lower() == focus_skill.lower()


def _matches_subskills(question: "_NormalizedToeicQuestion", subskills: list[str]) -> bool:
    return not subskills or any(item.lower() == question.subskillCode.lower() for item in subskills)


def _matches_review_focus(
    question: "_NormalizedToeicQuestion",
    part: int | None,
    skill: str | None,
    subskill: str | None,
    difficulty: str,
    source_question_id: int,
) -> bool:
    if question.question.id == source_question_id:
        return False
    if part and question.part != part:
        return False
    if skill and question.skillCode.lower() != skill.lower():
        return False
    if subskill and question.subskillCode.lower() != subskill.lower():
        return False
    return _matches_difficulty(question, difficulty)


def _take_balanced_questions(source: list["_NormalizedToeicQuestion"], count: int) -> list["_NormalizedToeicQuestion"]:
    grouped: dict[int, deque[_NormalizedToeicQuestion]] = {}
    for item in sorted(source, key=lambda row: (row.part, row.question.test, row.question.questionNumber)):
        grouped.setdefault(item.part, deque()).append(item)
    result: list[_NormalizedToeicQuestion] = []
    active = [queue for queue in grouped.values() if queue]
    while len(result) < count and active:
        for queue in list(active):
            if not queue:
                active.remove(queue)
                continue
            result.append(queue.popleft())
            if len(result) >= count:
                break
            if not queue:
                active.remove(queue)
    return result


def _resolve_part_name(part: int) -> str:
    return {
        1: "Photographs",
        2: "Question-Response",
        3: "Conversations",
        4: "Short Talks",
        5: "Incomplete Sentences",
        6: "Text Completion",
        7: "Reading Comprehension",
    }.get(part, f"Part {part}")


def _infer_section(part: int) -> str:
    return "Listening" if part <= 4 else "Reading"


def _build_listening_packs(summary: ToeicBundleSummaryDto) -> list[ToeicRecommendedPackDto]:
    result: list[ToeicRecommendedPackDto] = []
    _add_pack_if_available(result, summary, 1, "p1-photographs-boost", "Photographs boost", "listening", "Warm up with short picture items.", "starter", 12)
    _add_pack_if_available(result, summary, 2, "p2-question-response-drill", "Question-Response drill", "listening", "Rebuild quick listening reflexes.", "starter", 15)
    _add_pack_if_available(result, summary, 3, "p3-conversations-set", "Conversations set", "listening", "Move into short conversations next.", "intermediate", 9)
    result.append(ToeicRecommendedPackDto(id="p5-reading-bridge", part=5, title="Reading bridge", skill="reading", why="Keep reading active with a short Part 5 set.", difficulty="starter", suggestedQuestionCount=10, suggestedTests=[], audioReady=False))
    return result


def _build_reading_packs(summary: ToeicBundleSummaryDto) -> list[ToeicRecommendedPackDto]:
    result = [
        ToeicRecommendedPackDto(id="p5-grammar-vocab-core", part=5, title="Grammar + vocab core", skill="reading", why="Rebuild grammar and vocabulary accuracy.", difficulty="starter", suggestedQuestionCount=15, suggestedTests=[], audioReady=False),
        ToeicRecommendedPackDto(id="p6-text-completion-phase2", part=6, title="Text completion phase 2", skill="reading", why="Move into short reading passages next.", difficulty="intermediate", suggestedQuestionCount=8, suggestedTests=[], audioReady=False),
        ToeicRecommendedPackDto(id="p7-reading-comprehension-phase2", part=7, title="Reading comprehension phase 2", skill="reading", why="Extend into longer reading sets later.", difficulty="intermediate", suggestedQuestionCount=8, suggestedTests=[], audioReady=False),
    ]
    _add_pack_if_available(result, summary, 2, "p2-maintain-listening", "Maintain listening", "listening", "Keep listening reflexes active.", "starter", 10)
    return result


def _build_balanced_packs(summary: ToeicBundleSummaryDto) -> list[ToeicRecommendedPackDto]:
    result: list[ToeicRecommendedPackDto] = []
    _add_pack_if_available(result, summary, 1, "p1-balanced-start", "Balanced start - Part 1", "listening", "Start with a light listening warm-up.", "starter", 6)
    _add_pack_if_available(result, summary, 2, "p2-balanced-drill", "Balanced drill - Part 2", "listening", "Keep listening active with short prompts.", "starter", 10)
    result.append(ToeicRecommendedPackDto(id="p5-balanced-bridge", part=5, title="Balanced bridge - Part 5", skill="reading", why="Balance the session with a short grammar set.", difficulty="starter", suggestedQuestionCount=10, suggestedTests=[], audioReady=False))
    _add_pack_if_available(result, summary, 3, "p3-balanced-next", "Balanced next - Part 3", "listening", "Step into longer listening items next.", "intermediate", 9)
    return result


def _add_pack_if_available(result: list[ToeicRecommendedPackDto], summary: ToeicBundleSummaryDto, part: int, pack_id: str, title: str, skill: str, why: str, difficulty: str, suggested_question_count: int) -> None:
    info = next((item for item in summary.parts if item.part == part), None)
    if info is None:
        return
    result.append(
        ToeicRecommendedPackDto(
            id=pack_id,
            part=part,
            title=title,
            skill=skill,
            why=why,
            difficulty=difficulty,
            suggestedQuestionCount=suggested_question_count,
            suggestedTests=info.testsAvailable or [],
            audioReady=info.audioReady,
        )
    )


@dataclass
class _NormalizedToeicQuestion:
    uniqueKey: str
    question: ToeicRunnerQuestionDto
    skillCode: str
    subskillCode: str
    difficulty: str
    part: int
