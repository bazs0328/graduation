from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuizQuestionType(str, Enum):
    single = "single"
    judge = "judge"
    short = "short"


class QuizGenerateRequest(BaseModel):
    document_id: Optional[int] = None
    doc_ids: Optional[List[int]] = None
    count: int = Field(5, ge=1, le=20)
    types: List[QuizQuestionType] = Field(
        default_factory=lambda: [QuizQuestionType.single, QuizQuestionType.judge, QuizQuestionType.short]
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
    source_chunk_ids: List[int]
    related_concept: Optional[str] = None


class QuizGenerateResponse(BaseModel):
    quiz_id: int
    questions: List[QuizQuestionResponse]
