from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    MockTestAttempt,
    MockTestAttemptAnswer,
    PracticeAttempt,
    PracticeAttemptAnswer,
    ToeicPassage,
    ToeicQuestion,
    User,
    UserPartStat,
    UserRoadmap,
    UserRoadmapWeek,
    UserSkillAnalytics,
    UserSkillProfile,
)
from app.schemas.chat import ChatContextBundle, ChatContextSection, ChatIntent, ChatRequest
from app.utils.json_helpers import parse_string_list


class ChatContextService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build_context(self, user: User, request: ChatRequest, intent: ChatIntent) -> ChatContextBundle:
        bundle = ChatContextBundle()
        self._add_profile(bundle, user)
        self._add_recent_attempts(bundle, user.id)
        self._add_weak_skills(bundle, user)

        if request.question_id:
            self._add_question_context(bundle, user.id, request)
        elif intent == "explain_question":
            bundle.missing.append("question_id was not supplied, so the backend could not load the exact TOEIC question.")

        if request.attempt_id:
            self._add_attempt_context(bundle, user.id, request.attempt_id)
        elif intent in {"mock_test_review", "weak_skill_analysis"}:
            self._add_recent_wrong_answers(bundle, user.id)

        if intent == "study_plan":
            self._add_roadmap_context(bundle, user.id)
        if intent == "weekly_check_advice":
            self._add_weekly_check_context(bundle, user.id)

        return bundle

    def _add_profile(self, bundle: ChatContextBundle, user: User) -> None:
        weak_skills = parse_string_list(user.weak_skills_json)
        lines = [
            f"user_id={user.id}",
            f"current_score={user.current_score or 'unknown'}",
            f"target_score={user.target_score or 'unknown'}",
            f"study_minutes_per_day={user.study_minutes_per_day or 'unknown'}",
            f"exam_date={user.exam_date.isoformat() if user.exam_date else 'unknown'}",
            f"known_weak_skills={', '.join(weak_skills[:5]) if weak_skills else 'none recorded'}",
        ]
        self._add_section(bundle, "User profile", lines)

    def _add_recent_attempts(self, bundle: ChatContextBundle, user_id: int) -> None:
        practice_rows = self.db.scalars(
            select(PracticeAttempt)
            .where(PracticeAttempt.user_id == user_id)
            .order_by(func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc).desc())
            .limit(3)
        ).all()
        mock_rows = self.db.scalars(
            select(MockTestAttempt)
            .where(MockTestAttempt.user_id == user_id)
            .order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc())
            .limit(3)
        ).all()

        items: list[tuple[datetime, str]] = []
        for attempt in practice_rows:
            stamp = attempt.submitted_at_utc or attempt.created_at_utc or datetime.min
            items.append(
                (
                    stamp,
                    (
                        f"practice #{attempt.id}: {attempt.title}; mode={attempt.mode}; "
                        f"accuracy={self._fmt_number(attempt.accuracy_pct)}%; "
                        f"correct={attempt.correct_count}/{attempt.total_questions}; submitted={self._fmt_dt(stamp)}"
                    ),
                )
            )
        for attempt in mock_rows:
            stamp = attempt.submitted_at_utc or attempt.created_at_utc or datetime.min
            items.append(
                (
                    stamp,
                    (
                        f"mock-test #{attempt.id}: {attempt.title}; score={attempt.total_score or 'unknown'}; "
                        f"accuracy={self._fmt_number(attempt.accuracy_pct)}%; "
                        f"correct={attempt.correct_count}/{attempt.total_questions}; submitted={self._fmt_dt(stamp)}"
                    ),
                )
            )

        lines = [line for _, line in sorted(items, key=lambda item: item[0], reverse=True)[:4]]
        if lines:
            self._add_section(bundle, "Recent attempts", lines)
        else:
            bundle.missing.append("No recent practice or mock-test attempts were found.")

    def _add_weak_skills(self, bundle: ChatContextBundle, user: User) -> None:
        lines: list[str] = []
        analytics = self.db.scalar(select(UserSkillAnalytics).where(UserSkillAnalytics.user_id == user.id))
        if analytics:
            if analytics.weakest_skill or analytics.weakest_skill_label:
                lines.append(
                    f"weakest_skill={analytics.weakest_skill_label or analytics.weakest_skill}; weakest_part={analytics.weakest_part or 'unknown'}"
                )
            top_subskills = parse_string_list(analytics.top_weak_subskills_json)
            if top_subskills:
                lines.append(f"top_weak_subskills={', '.join(top_subskills[:5])}")

        skill_rows = self.db.scalars(
            select(UserSkillProfile)
            .where(UserSkillProfile.user_id == user.id, UserSkillProfile.attempt_count > 0)
            .order_by(UserSkillProfile.accuracy_pct, UserSkillProfile.attempt_count.desc())
            .limit(4)
        ).all()
        for row in skill_rows:
            lines.append(
                f"skill={row.skill_name or row.skill_code}; accuracy={self._fmt_number(row.accuracy_pct)}%; attempts={row.attempt_count}"
            )

        part_rows = self.db.scalars(
            select(UserPartStat)
            .where(UserPartStat.user_id == user.id, UserPartStat.attempt_count > 0)
            .order_by(UserPartStat.accuracy_pct, UserPartStat.attempt_count.desc())
            .limit(3)
        ).all()
        for row in part_rows:
            lines.append(
                f"part={row.part}; accuracy={self._fmt_number(row.accuracy_pct)}%; attempts={row.attempt_count}"
            )

        if lines:
            self._add_section(bundle, "Weak areas", lines[:8])
        else:
            bundle.missing.append("No weak-skill analytics were found.")

    def _add_question_context(self, bundle: ChatContextBundle, user_id: int, request: ChatRequest) -> None:
        docx_context = self._load_docx_question_context(request.question_id, request.question_text)
        if docx_context:
            bundle.question_id = docx_context.get("question_id")
            bundle.question_text = docx_context.get("question_text_en")
            bundle.passage_text = docx_context.get("passage_text")
            bundle.options = docx_context.get("options") or []
            bundle.correct_answer = docx_context.get("correct_answer_text")
            bundle.explanation = docx_context.get("explanation_detail")
            bundle.raw = docx_context

            lines = [
                f"question_id={docx_context.get('question_id')}",
                f"question_text_en={self._truncate(docx_context.get('question_text_en'), 700)}",
            ]
            if docx_context.get("passage_text"):
                lines.append(f"passage_text={self._truncate(docx_context.get('passage_text'), 800)}")
            if docx_context.get("options"):
                lines.append(
                    "options="
                    + "; ".join(
                        f"{item.get('label')}. {self._truncate(item.get('text'), 180)}"
                        for item in docx_context.get("options") or []
                    )
                )
            if docx_context.get("correct_answer_text"):
                lines.append(
                    f"correct_answer={docx_context.get('correct_option_label')}. {docx_context.get('correct_answer_text')}"
                )
            for key in [
                "translation_vi",
                "final_translation_vi",
                "explanation_detail",
                "option_analysis",
                "vocabulary_notes",
                "raw_block",
            ]:
                if docx_context.get(key):
                    lines.append(f"{key}={self._truncate(docx_context.get(key), 900)}")
            self._add_section(bundle, "Question context", lines)
            return

        question = self.db.scalar(
            select(ToeicQuestion)
            .options(
                joinedload(ToeicQuestion.passage).selectinload(ToeicPassage.assets),
                selectinload(ToeicQuestion.options),
                selectinload(ToeicQuestion.assets),
            )
            .where(ToeicQuestion.id == request.question_id)
        )
        if question is None:
            bundle.missing.append(f"question_id={request.question_id} was not found in ToeicQuestions.")
            return

        options = sorted(question.options, key=lambda item: (item.sort_order, item.option_key))
        correct_index = self._resolve_option_index(question.correct_option_key)
        selected_index = request.selected_answer_index
        source_answer = self._get_latest_answer_for_question(user_id, question.id)
        if selected_index is None and source_answer is not None:
            selected_index = source_answer.selected_answer_index

        lines = [
            f"question_id={question.id}; part={question.part}; question_number={question.question_number}; test={question.test_number or 'unknown'}",
            f"skill={question.skill_code or question.topic or 'unknown'}; subskill={question.subskill_code or 'unknown'}; difficulty={question.difficulty or 'unknown'}",
            f"question={self._truncate(question.question_text, 700)}",
        ]
        if question.passage and question.passage.passage_text:
            lines.append(f"passage={self._truncate(question.passage.passage_text, 800)}")
        if question.transcript:
            lines.append(f"transcript={self._truncate(question.transcript, 700)}")
        if options:
            option_text = "; ".join(
                f"{option.option_key or self._option_label(index)}. {self._truncate(option.option_text, 180)}"
                for index, option in enumerate(options)
            )
            lines.append(f"options={option_text}")
        if correct_index is not None:
            lines.append(f"correct_answer={self._answer_line(correct_index, options)}")
        if selected_index is not None:
            selected_line = self._answer_line(selected_index, options)
            if source_answer is not None:
                selected_line += f"; is_correct={bool(source_answer.is_correct)}"
            lines.append(f"user_selected_answer={selected_line}")
        if question.explanation:
            lines.append(f"existing_explanation={self._truncate(question.explanation, 700)}")

        self._add_section(bundle, "Question context", lines)

    def _add_attempt_context(self, bundle: ChatContextBundle, user_id: int, attempt_id: int) -> None:
        practice = self.db.scalar(
            select(PracticeAttempt)
            .options(selectinload(PracticeAttempt.answers))
            .where(PracticeAttempt.id == attempt_id, PracticeAttempt.user_id == user_id)
        )
        if practice is not None:
            self._add_practice_attempt_context(bundle, practice)
            return

        mock = self.db.scalar(
            select(MockTestAttempt)
            .options(selectinload(MockTestAttempt.answers))
            .where(MockTestAttempt.id == attempt_id, MockTestAttempt.user_id == user_id)
        )
        if mock is not None:
            self._add_mock_attempt_context(bundle, mock)
            return

        bundle.missing.append(f"attempt_id={attempt_id} was not found for this user.")

    def _add_practice_attempt_context(self, bundle: ChatContextBundle, attempt: PracticeAttempt) -> None:
        wrong_answers = [answer for answer in sorted(attempt.answers, key=lambda item: item.question_number or 0) if not answer.is_correct]
        lines = [
            f"practice_attempt_id={attempt.id}; title={attempt.title}; mode={attempt.mode}; parts={attempt.parts or 'unknown'}",
            f"accuracy={self._fmt_number(attempt.accuracy_pct)}%; correct={attempt.correct_count}/{attempt.total_questions}; score={attempt.score or 'unknown'}",
            f"time_spent_seconds={attempt.time_spent_seconds}; submitted={self._fmt_dt(attempt.submitted_at_utc or attempt.created_at_utc)}",
        ]
        for answer in wrong_answers[:5]:
            lines.append(self._saved_answer_line(answer))
        self._add_section(bundle, "Practice attempt context", lines)

    def _add_mock_attempt_context(self, bundle: ChatContextBundle, attempt: MockTestAttempt) -> None:
        wrong_answers = [answer for answer in sorted(attempt.answers, key=lambda item: item.question_number or 0) if not answer.is_correct]
        lines = [
            f"mock_test_attempt_id={attempt.id}; title={attempt.title}; status={attempt.status or 'unknown'}",
            f"total_score={attempt.total_score or 'unknown'}; listening={attempt.listening_score or 'unknown'}; reading={attempt.reading_score or 'unknown'}",
            f"accuracy={self._fmt_number(attempt.accuracy_pct)}%; correct={attempt.correct_count}/{attempt.total_questions}",
            f"time_spent_seconds={attempt.time_spent_seconds}; submitted={self._fmt_dt(attempt.submitted_at_utc or attempt.created_at_utc)}",
        ]
        for answer in wrong_answers[:6]:
            lines.append(self._saved_answer_line(answer))
        self._add_section(bundle, "Mock-test attempt context", lines)

    def _add_recent_wrong_answers(self, bundle: ChatContextBundle, user_id: int) -> None:
        practice_rows = self.db.execute(
            select(PracticeAttemptAnswer, func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc))
            .join(PracticeAttempt, PracticeAttempt.id == PracticeAttemptAnswer.practice_attempt_id)
            .where(PracticeAttempt.user_id == user_id, PracticeAttemptAnswer.is_correct.is_(False))
            .order_by(func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc).desc())
            .limit(4)
        ).all()
        mock_rows = self.db.execute(
            select(MockTestAttemptAnswer, func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc))
            .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
            .where(MockTestAttempt.user_id == user_id, MockTestAttemptAnswer.is_correct.is_(False))
            .order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc())
            .limit(4)
        ).all()

        rows: list[tuple[datetime, str]] = []
        for answer, stamp in practice_rows:
            rows.append((stamp or datetime.min, self._saved_answer_line(answer, source="practice")))
        for answer, stamp in mock_rows:
            rows.append((stamp or datetime.min, self._saved_answer_line(answer, source="mock-test")))

        lines = [line for _, line in sorted(rows, key=lambda item: item[0], reverse=True)[:6]]
        if lines:
            self._add_section(bundle, "Recent wrong answers", lines)
        else:
            bundle.missing.append("No recent wrong answers were found.")

    def _add_roadmap_context(self, bundle: ChatContextBundle, user_id: int) -> None:
        roadmap = self.db.scalar(
            select(UserRoadmap)
            .options(selectinload(UserRoadmap.weeks).selectinload(UserRoadmapWeek.items))
            .where(UserRoadmap.user_id == user_id, UserRoadmap.is_active.is_(True))
            .order_by(UserRoadmap.updated_at_utc.desc())
            .limit(1)
        )
        if roadmap is None:
            bundle.missing.append("No active roadmap was found.")
            return

        lines = [
            f"roadmap_id={roadmap.id}; title={roadmap.title}; total_weeks={roadmap.total_weeks}",
            f"weakest_skill={roadmap.weakest_skill_label or roadmap.weakest_skill or 'unknown'}; weakest_part={roadmap.weakest_part or 'unknown'}",
        ]
        weeks = sorted(roadmap.weeks, key=lambda item: item.week_number)
        current_weeks = [week for week in weeks if week.status != "completed"][:2] or weeks[:2]
        for week in current_weeks:
            lines.append(
                f"week {week.week_number}: {week.title}; status={week.status}; focus={week.focus_skill or 'unknown'}; part={week.focus_part or 'unknown'}"
            )
            for item in sorted(week.items, key=lambda value: value.sort_order)[:3]:
                lines.append(
                    f"  item={item.title}; type={item.item_type}; questions={item.question_count}; minutes={item.estimated_minutes}"
                )
        self._add_section(bundle, "Roadmap context", lines)

    def _add_weekly_check_context(self, bundle: ChatContextBundle, user_id: int) -> None:
        attempt = self.db.scalar(
            select(PracticeAttempt)
            .where(PracticeAttempt.user_id == user_id, PracticeAttempt.mode == "weekly-check")
            .order_by(func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc).desc())
            .limit(1)
        )
        if attempt is None:
            bundle.missing.append("No submitted weekly check was found.")
            return
        self._add_section(
            bundle,
            "Weekly check context",
            [
                f"weekly_check_attempt_id={attempt.id}; title={attempt.title}",
                f"accuracy={self._fmt_number(attempt.accuracy_pct)}%; correct={attempt.correct_count}/{attempt.total_questions}",
                f"parts={attempt.parts or 'unknown'}; difficulty={attempt.difficulty or 'unknown'}",
            ],
        )

    def _get_latest_answer_for_question(
        self,
        user_id: int,
        question_id: int,
    ) -> PracticeAttemptAnswer | MockTestAttemptAnswer | None:
        practice = self.db.scalar(
            select(PracticeAttemptAnswer)
            .join(PracticeAttempt, PracticeAttempt.id == PracticeAttemptAnswer.practice_attempt_id)
            .where(PracticeAttempt.user_id == user_id, PracticeAttemptAnswer.question_id == question_id)
            .order_by(func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc).desc())
            .limit(1)
        )
        mock = self.db.scalar(
            select(MockTestAttemptAnswer)
            .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
            .where(MockTestAttempt.user_id == user_id, MockTestAttemptAnswer.question_id == question_id)
            .order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc())
            .limit(1)
        )
        return practice or mock

    def _add_section(self, bundle: ChatContextBundle, title: str, lines: Iterable[str]) -> None:
        clean_lines = [self._truncate(line, 1200) for line in lines if line and line.strip()]
        if clean_lines:
            bundle.sections.append(ChatContextSection(title=title, lines=clean_lines[:10]))

    def _row_get(self, row: Any, *keys: str, default: Any = None) -> Any:
        if not row:
            return default
        row_keys = list(row.keys()) if hasattr(row, "keys") else []
        lower_lookup = {str(key).lower(): key for key in row_keys}
        for key in keys:
            if key in row_keys:
                value = row.get(key)
                if value not in (None, ""):
                    return value
            actual_key = lower_lookup.get(key.lower())
            if actual_key is not None:
                value = row.get(actual_key)
                if value not in (None, ""):
                    return value
        return default

    def _load_docx_question_context(self, question_id: int | None, expected_question_text: str | None = None) -> dict[str, Any]:
        if not question_id:
            return {}
        try:
            qid = int(question_id)
        except Exception:
            return {}

        question_row = None
        option_rows = []
        for table_prefix in ("dbo.", "QuanLyData.dbo."):
            try:
                question_row = self.db.execute(
                    text(
                        f"""
                        SELECT TOP 1 *
                        FROM {table_prefix}ToeicDocxQuestions
                        WHERE Id = :question_id
                        """
                    ),
                    {"question_id": qid},
                ).mappings().first()
                if not question_row:
                    continue
                option_rows = self.db.execute(
                    text(
                        f"""
                        SELECT *
                        FROM {table_prefix}ToeicDocxOptions
                        WHERE QuestionId = :question_id
                        ORDER BY SortOrder
                        """
                    ),
                    {"question_id": qid},
                ).mappings().all()
                break
            except Exception:
                continue

        if question_row and expected_question_text:
            actual_text = " ".join(str(self._row_get(question_row, "QuestionTextEn", "QuestionText", "Question") or "").split())
            expected_text = " ".join(str(expected_question_text or "").split())
            if actual_text != expected_text:
                question_row = None

        if not question_row:
            logger.info(
                "TOEIC Docx question context not found for received question_id=%s; attempting text-based fallback.",
                qid,
            )
            try:
                runner_row = self.db.execute(
                    text(
                        """
                        SELECT TOP 1 Id, TestNumber, Part, QuestionNumber, QuestionText
                        FROM dbo.ToeicQuestions
                        WHERE Id = :question_id
                        """
                    ),
                    {"question_id": qid},
                ).mappings().first()
                if runner_row:
                    mapped_row = self.db.execute(
                        text(
                            """
                            SELECT TOP 1 Id
                            FROM dbo.ToeicDocxQuestions
                            WHERE (:question_number IS NULL OR QuestionNumber = :question_number)
                              AND (:part IS NULL OR PartNumber = :part)
                              AND (:test_number IS NULL OR TestNumber = :test_number)
                              AND (:question_text = '' OR QuestionTextEn = :question_text)
                            ORDER BY Id
                            """
                        ),
                        {
                            "question_number": self._row_get(runner_row, "QuestionNumber"),
                            "part": self._row_get(runner_row, "Part"),
                            "test_number": self._row_get(runner_row, "TestNumber"),
                            "question_text": self._row_get(runner_row, "QuestionText", default=""),
                        },
                    ).mappings().first()
                    if mapped_row and mapped_row.get("Id"):
                        return self._load_docx_question_context(int(mapped_row.get("Id")), expected_question_text)
            except Exception:
                pass
            return self._load_runner_question_context(qid)

        correct_label = str(
            self._row_get(question_row, "CorrectOptionLabel", "CorrectOptionKey", "CorrectAnswer", "Answer", default="")
            or ""
        ).strip().upper()
        options = [
            {
                "id": self._row_get(row, "Id"),
                "question_id": self._row_get(row, "QuestionId"),
                "label": str(self._row_get(row, "OptionLabel", "OptionKey", "Label", default=self._option_label(index))).strip(),
                "text": str(self._row_get(row, "OptionTextEn", "OptionText", "Text", default="")).strip(),
                "is_correct": self._row_get(row, "IsCorrect"),
                "sort_order": self._row_get(row, "SortOrder"),
                "translation": self._row_get(row, "OptionTextVi", "TranslationVi", "OptionTranslationVi"),
                "analysis": self._row_get(row, "Analysis", "OptionAnalysis", "Explanation"),
            }
            for index, row in enumerate(option_rows)
        ]
        correct_answer_text = self._row_get(question_row, "CorrectAnswerText") or next(
            (item.get("text") for item in options if str(item.get("label") or "").strip().upper() == correct_label),
            None,
        )
        return {
            "question_id": self._row_get(question_row, "Id"),
            "source_file": self._row_get(question_row, "SourceFile"),
            "test_number": self._row_get(question_row, "TestNumber"),
            "part_number": self._row_get(question_row, "PartNumber"),
            "question_number": self._row_get(question_row, "QuestionNumber"),
            "question_text_en": self._row_get(question_row, "QuestionTextEn", "QuestionText", "Question"),
            "passage_text": self._row_get(question_row, "PassageText", "PassageTextEn", "Passage"),
            "options": options,
            "correct_option_label": correct_label or None,
            "correct_answer_text": correct_answer_text,
            "translation_vi": self._row_get(question_row, "TranslationVi"),
            "final_translation_vi": self._row_get(question_row, "FinalTranslationVi"),
            "explanation_detail": self._row_get(question_row, "ExplanationDetail", "Explanation"),
            "option_analysis": self._row_get(question_row, "OptionAnalysis"),
            "vocabulary_notes": self._row_get(question_row, "VocabularyNotes"),
            "raw_block": self._row_get(question_row, "RawBlock"),
        }

    def _load_runner_question_context(self, question_id: int) -> dict[str, Any]:
        try:
            question_row = self.db.execute(
                text(
                    """
                    SELECT TOP 1
                        q.Id,
                        q.TestNumber,
                        q.QuestionNumber,
                        q.Part,
                        q.QuestionText,
                        q.Explanation,
                        q.CorrectOptionKey,
                        q.Transcript,
                        q.SkillCode,
                        q.SubskillCode,
                        q.Topic,
                        q.Difficulty,
                        q.QuestionType,
                        p.Title AS PassageTitle,
                        p.PassageText
                    FROM dbo.ToeicQuestions q
                    LEFT JOIN dbo.ToeicPassages p ON p.Id = q.PassageId
                    WHERE q.Id = :question_id
                    """
                ),
                {"question_id": question_id},
            ).mappings().first()
        except Exception:
            logger.info("Could not load runner TOEIC question from dbo.ToeicQuestions.", exc_info=True)
            return {}

        if not question_row:
            return {}

        try:
            option_rows = self.db.execute(
                text(
                    """
                    SELECT Id, QuestionId, OptionKey, OptionText, SortOrder
                    FROM dbo.ToeicQuestionOptions
                    WHERE QuestionId = :question_id
                    ORDER BY SortOrder, Id
                    """
                ),
                {"question_id": question_id},
            ).mappings().all()
        except Exception:
            option_rows = []

        correct_label = str(self._row_get(question_row, "CorrectOptionKey", default="") or "").strip().upper()
        options = []
        for index, row in enumerate(option_rows):
            label = str(self._row_get(row, "OptionKey", default=self._option_label(index)) or "").strip().upper()
            option_text = str(self._row_get(row, "OptionText", default="") or "").strip()
            if not option_text:
                continue
            options.append(
                {
                    "id": self._row_get(row, "Id"),
                    "question_id": self._row_get(row, "QuestionId"),
                    "label": label or self._option_label(index),
                    "text": option_text,
                    "is_correct": label == correct_label if correct_label else None,
                    "sort_order": self._row_get(row, "SortOrder"),
                }
            )

        correct_answer_text = next(
            (item.get("text") for item in options if str(item.get("label") or "").strip().upper() == correct_label),
            None,
        )
        explanation = self._row_get(question_row, "Explanation")

        return {
            "question_id": self._row_get(question_row, "Id"),
            "test_number": self._row_get(question_row, "TestNumber"),
            "part_number": self._row_get(question_row, "Part"),
            "part": self._row_get(question_row, "Part"),
            "question_number": self._row_get(question_row, "QuestionNumber"),
            "question_text_en": self._row_get(question_row, "QuestionText"),
            "passage_text": self._row_get(question_row, "PassageText"),
            "transcript": self._row_get(question_row, "Transcript"),
            "options": options,
            "correct_option_label": correct_label or None,
            "correct_answer_text": correct_answer_text,
            "translation_vi": None,
            "final_translation_vi": None,
            "explanation_detail": explanation,
            "option_analysis": explanation,
            "vocabulary_notes": None,
            "raw_block": explanation,
            "skill": self._row_get(question_row, "SkillCode"),
            "subskill": self._row_get(question_row, "SubskillCode"),
            "topic": self._row_get(question_row, "Topic"),
            "difficulty": self._row_get(question_row, "Difficulty"),
            "question_type": self._row_get(question_row, "QuestionType"),
            "sql_source": "dbo.ToeicQuestions",
        }

    def _saved_answer_line(self, answer: PracticeAttemptAnswer | MockTestAttemptAnswer, source: str | None = None) -> str:
        prefix = f"{source}: " if source else ""
        explanation = f"; explanation={self._truncate(answer.explanation, 220)}" if getattr(answer, "explanation", None) else ""
        return (
            f"{prefix}question_id={answer.question_id}; number={answer.question_number or 'unknown'}; "
            f"part={answer.part or 'unknown'}; skill={answer.skill or 'unknown'}; "
            f"selected_index={answer.selected_answer_index}; correct_index={answer.correct_answer_index}; "
            f"is_correct={bool(answer.is_correct)}{explanation}"
        )

    def _answer_line(self, index: int, options: list) -> str:
        label = self._option_label(index)
        if 0 <= index < len(options):
            return f"{label}. {self._truncate(options[index].option_text, 220)}"
        return f"{label}."

    def _option_label(self, index: int) -> str:
        return chr(ord("A") + index) if 0 <= index < 26 else str(index)

    def _resolve_option_index(self, option_key: str | None) -> int | None:
        if not option_key:
            return None
        value = option_key.strip().upper()
        if not value:
            return None
        return ord(value[0]) - ord("A") if "A" <= value[0] <= "Z" else None

    def _truncate(self, value: str | None, limit: int) -> str:
        text = " ".join((value or "").strip().split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _fmt_number(self, value: Decimal | int | float | None) -> str:
        if value is None:
            return "unknown"
        return f"{float(value):.1f}".rstrip("0").rstrip(".")

    def _fmt_dt(self, value: datetime | None) -> str:
        return value.isoformat() if value else "unknown"


def _normalize_lookup_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _snippet_around_term(value: Any, target_term: str, limit: int = 360) -> str:
    text_value = re.sub(r"\s+", " ", str(value or "").strip())
    if not text_value:
        return ""
    match = re.search(rf"\b{re.escape(target_term.lower())}\b", text_value, flags=re.IGNORECASE)
    if not match:
        return ""
    start = max(0, match.start() - 140)
    end = min(len(text_value), match.end() + 220)
    snippet = text_value[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text_value):
        snippet += "..."
    return snippet[:limit]


def find_term_context(question_context: dict[str, Any], target_term: str) -> dict[str, Any]:
    target = (target_term or "").strip()
    if not target:
        return {}

    sources: list[dict[str, str]] = []
    option_match = None
    for option in question_context.get("options") or []:
        option_text = str(option.get("text") or "")
        if re.search(rf"\b{re.escape(target)}\b", option_text, flags=re.IGNORECASE):
            option_match = option
            sources.append({"field": "ToeicDocxOptions.OptionTextEn", "snippet": option_text})
            break

    for key, field_name in [
        ("vocabulary_notes", "ToeicDocxQuestions.VocabularyNotes"),
        ("explanation_detail", "ToeicDocxQuestions.ExplanationDetail"),
        ("option_analysis", "ToeicDocxQuestions.OptionAnalysis"),
        ("translation_vi", "ToeicDocxQuestions.TranslationVi"),
        ("final_translation_vi", "ToeicDocxQuestions.FinalTranslationVi"),
        ("raw_block", "ToeicDocxQuestions.RawBlock"),
    ]:
        snippet = _snippet_around_term(question_context.get(key), target)
        if snippet:
            sources.append({"field": field_name, "snippet": snippet})
            if key != "raw_block" and len(sources) >= 4:
                break

    if not sources:
        return {}

    return {
        "target_term": target,
        "target_option_label": option_match.get("label") if option_match else None,
        "option": option_match,
        "sources": sources[:5],
    }


def _clean_definition_meaning(value: Any) -> str:
    text_value = re.sub(r"\s+", " ", str(value or "").strip())
    text_value = re.sub(r"[\s.;:]+$", "", text_value)
    return text_value.strip(" \"'\u201c\u201d")


def _parse_definition_from_text(
    text_value: Any,
    target_term: str,
    target_option_label: str | None = None,
) -> dict[str, Any]:
    source = re.sub(r"\s+", " ", str(text_value or "").strip())
    term = (target_term or "").strip()
    if not source or not term:
        return {}

    label_part = rf"\({re.escape(target_option_label)}\)\s*" if target_option_label else r"(?:\(([A-D])\)\s*)?"
    entry_pattern = rf"{label_part}{re.escape(term)}\s*:\s*(?P<body>.*?)(?=(?:\([A-D]\)\s*[A-Za-z]|$))"
    match = re.search(entry_pattern, source, flags=re.IGNORECASE | re.DOTALL)
    if match:
        body = match.group("body")
        meaning_match = re.search(
            r"(?:Ngh\u0129a|Nghia)\s+l\u00e0\s+(?P<meaning>[^.。\n]+)",
            body,
            flags=re.IGNORECASE,
        )
        if meaning_match:
            status = _normalize_lookup_text(body)
            return {
                "term": term,
                "meaning": _clean_definition_meaning(meaning_match.group("meaning")),
                "option_label": target_option_label or (match.group(1).upper() if match.lastindex and match.group(1) else None),
                "is_correct": True if "dap an dung" in status else False if "sai" in status else None,
            }

    for pattern in [
        rf"{re.escape(term)}\s+(?:ngh\u0129a|nghia)\s+l\u00e0\s+(?P<meaning>[^.。\n]+)",
        rf"{re.escape(term)}\s*=\s*(?P<meaning>[^.;\n]+)",
    ]:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            return {
                "term": term,
                "meaning": _clean_definition_meaning(match.group("meaning")),
                "option_label": target_option_label,
                "is_correct": None,
            }
    return {}


def find_term_definition(
    question_context: dict[str, Any],
    target_term: str | None,
    target_option_label: str | None = None,
) -> dict[str, Any]:
    option_match = None
    if target_option_label:
        for option in question_context.get("options") or []:
            if str(option.get("label") or "").strip().upper() == target_option_label.upper():
                option_match = option
                break

    target = (target_term or "").strip()
    if option_match and not target:
        target = str(option_match.get("text") or "").strip()

    if not option_match and target:
        for option in question_context.get("options") or []:
            if re.search(rf"\b{re.escape(target)}\b", str(option.get("text") or ""), flags=re.IGNORECASE):
                option_match = option
                break

    if not target:
        return {}

    option_label = str(option_match.get("label") or target_option_label or "").strip().upper() if option_match or target_option_label else None
    sources = [
        ("ToeicDocxOptions.Analysis", option_match.get("analysis") if option_match else None),
        ("ToeicDocxOptions.TranslationVi", option_match.get("translation") if option_match else None),
        ("ToeicDocxQuestions.VocabularyNotes", question_context.get("vocabulary_notes")),
        ("ToeicDocxQuestions.OptionAnalysis", question_context.get("option_analysis")),
        ("ToeicDocxQuestions.ExplanationDetail", question_context.get("explanation_detail")),
        ("ToeicDocxQuestions.FinalTranslationVi", question_context.get("final_translation_vi")),
        ("ToeicDocxQuestions.TranslationVi", question_context.get("translation_vi")),
        ("ToeicDocxQuestions.RawBlock", question_context.get("raw_block")),
    ]

    for field, source_text in sources:
        parsed = _parse_definition_from_text(source_text, target, option_label)
        if parsed.get("meaning"):
            parsed["source_field"] = field
            parsed["option"] = option_match
            return parsed

    if option_match:
        return {
            "term": target,
            "meaning": None,
            "option_label": option_label,
            "is_correct": option_match.get("is_correct"),
            "source_field": "ToeicDocxOptions.OptionTextEn",
            "option": option_match,
        }
    return {}
