from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.diagnostic import DiagnosticSubmitRequest
from app.services.diagnostic import get_diagnostic_questions, submit_diagnostic
from app.services.weighted_score import compute_weight_score_fields
from app.utils.json_helpers import parse_string_list


router = APIRouter()


@router.get("/api/diagnostic/questions")
def questions(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    _ = user_id
    return get_diagnostic_questions(db)


@router.get("/api/diagnostic/latest")
def latest(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    row = db.execute(
        text(
            """
            SELECT TOP 1
                Id,
                EstimatedScore,
                LevelName,
                LevelRange,
                Theta,
                AccuracyPct,
                CorrectCount,
                TotalQuestions,
                WeakSubskillsJson,
                SubmittedAtUtc,
                CreatedAtUtc
            FROM dbo.DiagnosticAttempts
            WHERE UserId = :user_id
            ORDER BY COALESCE(SubmittedAtUtc, CreatedAtUtc) DESC, Id DESC
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    if row is None:
        return JSONResponse(
            status_code=404,
            content={"message": "No placement test result was found for this user."},
        )
    try:
        weight_rows = db.execute(
            text(
                """
                SELECT
                    a.QuestionId,
                    a.SelectedAnswerIndex,
                    a.IsCorrect,
                    q.LegacyQuestionId
                FROM dbo.DiagnosticAttemptAnswers a
                LEFT JOIN dbo.ToeicQuestions q
                    ON q.Id = a.QuestionId
                WHERE a.DiagnosticAttemptId = :attempt_id
                """
            ),
            {"attempt_id": int(row["Id"])},
        ).mappings().all()
        weight_fields = compute_weight_score_fields(
            [
                {
                    "item_id": int(item.get("LegacyQuestionId") or item.get("QuestionId") or 0),
                    "question_id": item.get("QuestionId"),
                    "selected_answer_index": item.get("SelectedAnswerIndex"),
                    "is_correct": bool(item.get("IsCorrect")),
                }
                for item in weight_rows
            ]
        )
    except Exception:
        weight_fields = compute_weight_score_fields([])
    return {
        "id": int(row["Id"]),
        "estimatedScore": int(row.get("EstimatedScore") or 0),
        **weight_fields,
        "estimatedLevel": row.get("LevelName") or "",
        "levelRange": row.get("LevelRange") or "",
        "theta": float(row["Theta"]) if row.get("Theta") is not None else None,
        "accuracy": float(row.get("AccuracyPct") or 0),
        "correctCount": int(row.get("CorrectCount") or 0),
        "totalQuestions": int(row.get("TotalQuestions") or 0),
        "weakSubskills": parse_string_list(row.get("WeakSubskillsJson")),
        "submittedAtUtc": row.get("SubmittedAtUtc") or row.get("CreatedAtUtc"),
    }


@router.post("/api/diagnostic/submit")
def submit(
    payload: DiagnosticSubmitRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _ = user_id
    return submit_diagnostic(db, payload)
