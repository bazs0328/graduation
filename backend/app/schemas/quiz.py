from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class QuizBase(BaseModel):
    session_id: str = Field(default="default", min_length=1)
    document_id: Optional[int] = None
    difficulty_plan_json: Optional[Dict[str, Any]] = None


class QuizCreate(QuizBase):
    pass


class QuizRead(QuizBase):
    id: int
    created_at: Optional[datetime] = None


class QuizQuestionBase(BaseModel):
    quiz_id: int
    type: str
    difficulty: str
    stem: str
    options_json: Optional[Any] = None
    answer_json: Optional[Any] = None
    explanation: Optional[str] = None
    related_concept: Optional[str] = None
    source_chunk_ids_json: Optional[Any] = None


class QuizQuestionCreate(QuizQuestionBase):
    pass


class QuizQuestionRead(QuizQuestionBase):
    id: int
    created_at: Optional[datetime] = None


class QuizAttemptBase(BaseModel):
    quiz_id: int
    score: Optional[float] = None
    accuracy: Optional[float] = None
    summary_json: Optional[Any] = None


class QuizAttemptCreate(QuizAttemptBase):
    pass


class QuizAttemptRead(QuizAttemptBase):
    id: int
    submitted_at: Optional[datetime] = None


class ConceptStatBase(BaseModel):
    session_id: str = Field(..., min_length=1)
    concept: str = Field(..., min_length=1)
    correct_count: int = 0
    wrong_count: int = 0
    last_seen: Optional[datetime] = None


class ConceptStatRead(ConceptStatBase):
    id: int


class LearnerProfileBase(BaseModel):
    session_id: str = Field(..., min_length=1)
    ability_level: Optional[str] = None
    theta: Optional[float] = None
    frustration_score: int = 0
    last_updated: Optional[datetime] = None


class LearnerProfileRead(LearnerProfileBase):
    id: int
