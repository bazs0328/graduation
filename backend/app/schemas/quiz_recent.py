from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuizRecentRequest(BaseModel):
    limit: int = Field(5, ge=1, le=20)


class QuizRecentItem(BaseModel):
    quiz_id: int
    submitted_at: Optional[datetime] = None
    score: Optional[float] = None
    accuracy: Optional[float] = None
    difficulty_plan: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None


class QuizRecentResponse(BaseModel):
    items: List[QuizRecentItem]
