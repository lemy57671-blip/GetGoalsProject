from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.diagnostic import (
    DiagnosticAnalysisDto,
    DiagnosticAssetDto,
    DiagnosticLevelDto,
    DiagnosticQuestionDto,
    DiagnosticQuestionsResponse,
    DiagnosticRoadmapWeekDto,
    DiagnosticSkillStatDto,
    DiagnosticSubskillRowDto,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
    DiagnosticTestInfoDto,
    DiagnosticTopErrorDto,
    DiagnosticWrongItemDto,
)
from app.services.irt_scoring import score_diagnostic_with_rasch
from app.services.weighted_score import compute_weight_score_fields


DIAGNOSTIC_SET_CODE = "DIAGNOSTIC_35"


@dataclass
class _StatBucket:
    correct: int = 0
    total: int = 0


@dataclass
class _DiagnosticAsset:
    path: str


@dataclass
class _DiagnosticBankQuestion:
    id: int
    legacy_id: int | None
    question_number: int
    question: str
    options: list[str]
    correctAnswerIndex: int | None
    skill: str | None
    subskill: str | None
    type: str | None
    image: _DiagnosticAsset | None = None
    audio: _DiagnosticAsset | None = None


def get_diagnostic_questions(db: Session) -> DiagnosticQuestionsResponse:
    questions = _load_bank(db)

    return DiagnosticQuestionsResponse(
        test_info=DiagnosticTestInfoDto(total_questions=len(questions)),
        questions=[_map_question(item) for item in questions],
    )


def submit_diagnostic(db: Session, payload: DiagnosticSubmitRequest) -> DiagnosticSubmitResponse:
    questions = _load_bank(db)
    answers = _normalize_answers(payload.answers)

    total = len(questions)
    answered_count = 0
    correct_count = 0

    wrong_items: list[DiagnosticWrongItemDto] = []
    skill_buckets: dict[str, _StatBucket] = {}
    subskill_buckets: dict[str, _StatBucket] = {}
    error_counter: Counter[str] = Counter()

    # Dữ liệu dùng để tính Rasch:
    # item_id = ToeicQuestions.LegacyQuestionId
    # is_correct = user đúng/sai
    rasch_items: list[dict] = []
    weight_items: list[dict] = []

    for index, question in enumerate(questions):
        selected = answers.get(index)

        if selected is None:
            selected = answers.get(question.id)

        if selected is None and question.legacy_id is not None:
            selected = answers.get(question.legacy_id)

        correct_index = question.correctAnswerIndex

        # Bám sát logic cũ: câu bỏ trống thì không đưa vào chấm theta.
        if selected is None:
            continue

        answered_count += 1

        is_correct = correct_index is not None and selected == correct_index
        weight_items.append(
            {
                "item_id": int(question.legacy_id or question.id),
                "question_id": int(question.id),
                "is_correct": bool(is_correct),
                "selected_answer_index": selected,
            }
        )

        if question.legacy_id is not None:
            rasch_items.append(
                {
                    "item_id": int(question.legacy_id),
                    "is_correct": bool(is_correct),
                }
            )

        if is_correct:
            correct_count += 1

        skill = _normalize_label(question.skill, "general_english")
        subskill = _normalize_label(question.subskill, skill)

        skill_bucket = skill_buckets.setdefault(skill, _StatBucket())
        subskill_bucket = subskill_buckets.setdefault(subskill, _StatBucket())

        skill_bucket.total += 1
        subskill_bucket.total += 1

        if is_correct:
            skill_bucket.correct += 1
            subskill_bucket.correct += 1
        else:
            error_counter[subskill] += 1

            wrong_items.append(
                DiagnosticWrongItemDto(
                    id=question.id,
                    skill=skill,
                    subskill=subskill,
                    questionText=question.question,
                    chosen=selected,
                    correct=correct_index,
                    options=list(question.options),
                )
            )

    accuracy_pct = 0 if answered_count == 0 else int(round((correct_count / answered_count) * 100))

    # Điểm rule-based cũ chỉ giữ làm fallback.
    score_rule = _resolve_score(accuracy_pct)
    fallback_level = _resolve_level(accuracy_pct)

    # Điểm chính dùng Rasch/IRT.
    rasch_result = score_diagnostic_with_rasch(rasch_items)
    weight_score_fields = compute_weight_score_fields(weight_items)

    score = int(rasch_result.get("estimated_score") or score_rule)

    level = DiagnosticLevelDto(
        code=str(rasch_result.get("level_code") or fallback_level.code),
        name=str(rasch_result.get("level_name") or fallback_level.name),
        range=str(rasch_result.get("level_range") or fallback_level.range),
    )

    skill_stats = {
        key: DiagnosticSkillStatDto(
            correct=value.correct,
            total=value.total,
            acc=_percent(value.correct, value.total),
        )
        for key, value in sorted(skill_buckets.items())
    }

    sorted_subskills = sorted(
        (
            DiagnosticSubskillRowDto(
                subskill=key,
                correct=value.correct,
                total=value.total,
                acc=_percent(value.correct, value.total),
            )
            for key, value in subskill_buckets.items()
        ),
        key=lambda item: (item.acc, item.total, item.subskill),
    )

    weak_subskills = [item.subskill for item in sorted_subskills if item.total > 0][:5]

    strong_subskills = [
        item.subskill
        for item in sorted(
            sorted_subskills,
            key=lambda item: (-item.acc, -item.total, item.subskill),
        )[:5]
    ]

    top_errors = [
        DiagnosticTopErrorDto(type=key, count=count)
        for key, count in error_counter.most_common(5)
    ]

    return DiagnosticSubmitResponse(
        analysis=DiagnosticAnalysisDto(
            score=score,
            **weight_score_fields,
            level=level,
            accuracyPct=accuracy_pct,
            correctCount=correct_count,
            answeredCount=answered_count,
            total=total,
            skillStats=skill_stats,
            subskillRows=sorted_subskills,
            weakSubskills=weak_subskills,
            strongSubskills=strong_subskills,
            topErrors=top_errors,
            wrongList=wrong_items[:20],
        ),
        roadmap=_build_roadmap(payload, weak_subskills, strong_subskills, level),
    )


def _load_bank(db: Session) -> list[_DiagnosticBankQuestion]:
    """
    Lấy đúng bộ bài test đầu vào từ SQL:
    dbo.ToeicSets.Code = 'DIAGNOSTIC_35'
    """

    question_rows = db.execute(
        text(
            """
            SELECT
                q.Id,
                q.LegacyQuestionId,
                q.QuestionNumber,
                q.QuestionText,
                q.CorrectOptionKey,
                q.SkillCode,
                q.SubskillCode,
                q.QuestionType
            FROM dbo.ToeicQuestions q
            INNER JOIN dbo.ToeicSets s
                ON s.Id = q.SetId
            WHERE
                s.Code = :set_code
                AND ISNULL(s.IsActive, 1) = 1
                AND ISNULL(q.IsActive, 1) = 1
            ORDER BY
                q.QuestionNumber ASC,
                q.SortOrder ASC,
                q.Id ASC
            """
        ),
        {"set_code": DIAGNOSTIC_SET_CODE},
    ).mappings().all()

    if not question_rows:
        return []

    question_ids = [int(row["Id"]) for row in question_rows]
    question_ids_csv = ",".join(str(item) for item in question_ids)

    options_by_question_id: dict[int, list[tuple[int, str, str]]] = {}
    assets_by_question_id: dict[int, dict[str, str]] = {}

    option_rows = db.execute(
        text(
            """
            SELECT
                QuestionId,
                OptionKey,
                OptionText,
                SortOrder
            FROM dbo.ToeicQuestionOptions
            WHERE QuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:question_ids_csv, ',')
            )
            ORDER BY
                QuestionId ASC,
                SortOrder ASC,
                OptionKey ASC
            """
        ),
        {"question_ids_csv": question_ids_csv},
    ).mappings().all()

    for row in option_rows:
        question_id = int(row["QuestionId"])
        sort_order = int(row["SortOrder"] or 0)
        option_key = str(row["OptionKey"] or "")
        option_text = str(row["OptionText"] or "")

        options_by_question_id.setdefault(question_id, []).append(
            (sort_order, option_key, option_text)
        )

    asset_rows = db.execute(
        text(
            """
            SELECT
                QuestionId,
                AssetType,
                RelativePath,
                SortOrder
            FROM dbo.ToeicQuestionAssets
            WHERE QuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:question_ids_csv, ',')
            )
            ORDER BY
                QuestionId ASC,
                SortOrder ASC,
                Id ASC
            """
        ),
        {"question_ids_csv": question_ids_csv},
    ).mappings().all()

    for row in asset_rows:
        question_id = int(row["QuestionId"])
        asset_type = str(row["AssetType"] or "").strip().lower()
        relative_path = str(row["RelativePath"] or "").strip()

        if not asset_type or not relative_path:
            continue

        assets_by_question_id.setdefault(question_id, {})

        if asset_type not in assets_by_question_id[question_id]:
            assets_by_question_id[question_id][asset_type] = relative_path

    questions: list[_DiagnosticBankQuestion] = []

    for row in question_rows:
        question_id = int(row["Id"])

        option_items = sorted(
            options_by_question_id.get(question_id, []),
            key=lambda item: (item[0], item[1]),
        )

        options = [item[2] for item in option_items]

        assets = assets_by_question_id.get(question_id, {})
        image_path = assets.get("image") or assets.get("graphic")
        audio_path = assets.get("audio")

        questions.append(
            _DiagnosticBankQuestion(
                id=question_id,
                legacy_id=row["LegacyQuestionId"],
                question_number=int(row["QuestionNumber"] or 0),
                question=str(row["QuestionText"] or ""),
                options=options,
                correctAnswerIndex=_option_key_to_index(row["CorrectOptionKey"]),
                skill=row["SkillCode"],
                subskill=row["SubskillCode"],
                type=row["QuestionType"] or "diagnostic_mcq",
                image=_DiagnosticAsset(path=image_path) if image_path else None,
                audio=_DiagnosticAsset(path=audio_path) if audio_path else None,
            )
        )

    return questions


def _map_question(question: _DiagnosticBankQuestion) -> DiagnosticQuestionDto:
    return DiagnosticQuestionDto(
        id=question.id,
        question=question.question,
        options=list(question.options),

        # Giai đoạn test giữ correct để frontend cũ không vỡ.
        # Khi chạy thật nên đổi thành correct=None để tránh lộ đáp án.
        correct=question.correctAnswerIndex,

        skill=question.skill,
        subskill=question.subskill,
        prompt_type=question.type,
        image=DiagnosticAssetDto(path=question.image.path) if question.image else None,
        audio=DiagnosticAssetDto(path=question.audio.path) if question.audio else None,
    )


def _normalize_answers(raw: dict[str, int]) -> dict[int, int]:
    normalized: dict[int, int] = {}

    for key, value in raw.items():
        try:
            normalized[int(key)] = int(value)
        except (TypeError, ValueError):
            continue

    return normalized


def _normalize_label(value: str | None, fallback: str) -> str:
    normalized = (value or "").strip().lower().replace(" ", "_")
    return normalized or fallback


def _percent(correct: int, total: int) -> float:
    return 0 if total <= 0 else round((correct / total) * 100, 2)


def _option_key_to_index(option_key: str | None) -> int | None:
    if not option_key:
        return None

    key = option_key.strip().upper()

    if not key:
        return None

    first = key[0]

    if "A" <= first <= "Z":
        return ord(first) - ord("A")

    return None


def _resolve_score(accuracy_pct: int) -> int:
    score = int(round(5 + (accuracy_pct / 100) * 985))
    return max(5, min(score, 990))


def _resolve_level(accuracy_pct: int) -> DiagnosticLevelDto:
    if accuracy_pct < 35:
        return DiagnosticLevelDto(code="starter", name="Starter", range="250-450")

    if accuracy_pct < 55:
        return DiagnosticLevelDto(code="elementary", name="Elementary", range="450-600")

    if accuracy_pct < 75:
        return DiagnosticLevelDto(code="intermediate", name="Intermediate", range="600-750")

    if accuracy_pct < 90:
        return DiagnosticLevelDto(
            code="upper_intermediate",
            name="Upper Intermediate",
            range="750-850",
        )

    return DiagnosticLevelDto(code="advanced", name="Advanced", range="850-990")


def _build_roadmap(
    payload: DiagnosticSubmitRequest,
    weak_subskills: list[str],
    strong_subskills: list[str],
    level: DiagnosticLevelDto,
) -> list[DiagnosticRoadmapWeekDto]:
    total_weeks = max(1, min(payload.weeks or 8, 12))
    minutes_per_day = max(10, payload.minutes_per_day or 30)

    focus_pool = weak_subskills or strong_subskills or [level.code]

    roadmap: list[DiagnosticRoadmapWeekDto] = []

    for week_number in range(1, total_weeks + 1):
        focus = focus_pool[(week_number - 1) % len(focus_pool)]
        focus_label = focus.replace("_", " ")

        roadmap.append(
            DiagnosticRoadmapWeekDto(
                week=week_number,
                focus=focus,
                title=f"Week {week_number} - {focus_label.title()}",
                tasks=[
                    f"Study {focus_label} for {minutes_per_day} minutes each day.",
                    f"Complete one focused TOEIC block and review all mistakes in {focus_label}.",
                    f"End the week with a mixed review set and note three takeaways for {focus_label}.",
                ],
            )
        )

    return roadmap
