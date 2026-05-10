from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
_schema_ready = False


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "20260508_review_queue_runtime_sources.sql"
)

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "dbo.ReviewQueue": [
        "Id",
        "UserId",
        "Source",
        "AttemptId",
        "QuestionId",
        "RuntimeQuestionId",
        "QuestionNumber",
        "Part",
        "Section",
        "SkillCode",
        "ReviewReason",
        "SelectedOptionKey",
        "CorrectOptionKey",
        "IsCorrect",
        "IsSkipped",
        "IsActive",
        "LastAnsweredAtUtc",
        "CreatedAtUtc",
        "UpdatedAtUtc",
    ],
    "dbo.UserQuestionNotes": [
        "UserId",
        "QuestionId",
        "Source",
        "AttemptId",
        "RuntimeQuestionId",
        "DiagnosticQuestionId",
        "NoteText",
        "CreatedAt",
        "UpdatedAt",
        "CreatedAtUtc",
        "UpdatedAtUtc",
        "IsActive",
    ],
    "dbo.UserQuestionHighlights": [
        "UserId",
        "QuestionId",
        "Source",
        "AttemptId",
        "RuntimeQuestionId",
        "DiagnosticQuestionId",
        "TargetType",
        "TargetKey",
        "SelectedText",
        "HighlightText",
        "StartOffset",
        "EndOffset",
        "Color",
        "NoteText",
        "CreatedAt",
        "UpdatedAt",
        "CreatedAtUtc",
        "UpdatedAtUtc",
        "IsActive",
    ],
    "dbo.UserQuestionBookmarks": [
        "UserId",
        "QuestionId",
        "Source",
        "AttemptId",
        "RuntimeQuestionId",
        "DiagnosticQuestionId",
        "CreatedAt",
        "CreatedAtUtc",
        "UpdatedAtUtc",
        "IsActive",
    ],
}


def _split_sql_batches(script: str) -> list[str]:
    batches: list[str] = []
    current: list[str] = []

    for line in script.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
            continue
        current.append(line)

    batch = "\n".join(current).strip()
    if batch:
        batches.append(batch)
    return batches


def _verify_review_schema(db: Session) -> None:
    missing: list[str] = []
    for table_name, columns in REQUIRED_COLUMNS.items():
        safe_table_name = table_name.replace("'", "''")
        table_exists = db.execute(
            text(f"SELECT OBJECT_ID(N'{safe_table_name}', N'U')")
        ).scalar()
        if table_exists is None:
            missing.append(f"{table_name}.* (table missing)")
            continue
        for column_name in columns:
            safe_column_name = column_name.replace("'", "''")
            column_length = db.execute(
                text(f"SELECT COL_LENGTH(N'{safe_table_name}', N'{safe_column_name}')")
            ).scalar()
            if column_length is None:
                missing.append(f"{table_name}.{column_name}")

    if missing:
        raise RuntimeError(
            "Review schema migration did not create required columns: "
            + ", ".join(missing)
        )


def ensure_review_schema(db: Session) -> None:
    global _schema_ready
    if _schema_ready:
        return

    try:
        script = MIGRATION_PATH.read_text(encoding="utf-8")
        batches = _split_sql_batches(script)
        for index, batch in enumerate(batches, start=1):
            try:
                db.execute(text(batch))
                db.commit()
            except Exception as exc:
                db.rollback()
                snippet = " ".join(batch.split())[:500]
                logger.exception(
                    "Review schema guard failed at batch %s/%s. Batch starts with: %s",
                    index,
                    len(batches),
                    snippet,
                )
                raise RuntimeError(
                    f"Review schema guard failed at batch {index}/{len(batches)}: {exc}"
                ) from exc
        _verify_review_schema(db)
        _schema_ready = True
    except Exception:
        db.rollback()
        logger.exception("Review schema guard failed.")
        raise
