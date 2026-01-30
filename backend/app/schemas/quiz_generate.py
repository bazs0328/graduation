from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuizQuestionType(str, Enum):
    single = "single"
    judge = "judge"
    short = "short"
    fill_blank = "fill_blank"
    calculation = "calculation"
    written = "written"


class QuizGenerateRequest(BaseModel):
    document_id: Optional[int] = None
    doc_ids: Optional[List[int]] = None
    count: int = Field(5, ge=1, le=20)
    types: List[QuizQuestionType] = Field(
        default_factory=lambda: [
            QuizQuestionType.single,
            QuizQuestionType.judge,
            QuizQuestionType.short,
            QuizQuestionType.fill_blank,
            QuizQuestionType.calculation,
            QuizQuestionType.written,
        ]
    )
    focus_concepts: Optional[List[str]] = None


class QuizQuestionResponse(BaseModel):
    question_id: int
    type: str
    difficulty: str
    stem: str
    options: Optional[List[str]] = None
    answer: Dict[str, Any]
    explanation: Optional[str] = None
    difficulty_reason: Optional[str] = None
    key_points: Optional[List[str]] = None
    review_suggestion: Optional[str] = None
    next_step: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None
    source_chunk_ids: List[int]
    related_concept: Optional[str] = None


class QuizGenerateResponse(BaseModel):
    quiz_id: int
    difficulty_plan: Dict[str, int]
    questions: List[QuizQuestionResponse]
