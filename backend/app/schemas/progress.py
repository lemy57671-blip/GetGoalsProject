from __future__ import annotations

from pydantic import BaseModel


class ProgressLogRequest(BaseModel):
    courseId: int
    minutesLearned: int
    progressDelta: int
