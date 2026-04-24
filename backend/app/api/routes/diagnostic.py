from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.diagnostic import DiagnosticSubmitRequest
from app.services.diagnostic import get_diagnostic_questions, submit_diagnostic


router = APIRouter()


@router.get("/api/diagnostic/questions")
def questions(db: Session = Depends(get_db)):
    return get_diagnostic_questions(db)


@router.post("/api/diagnostic/submit")
def submit(payload: DiagnosticSubmitRequest, db: Session = Depends(get_db)):
    return submit_diagnostic(db, payload)
