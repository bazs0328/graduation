from typing import Any, List, Optional

from pydantic import BaseModel, Field


class QuizSubmitAnswer(BaseModel):
    question_id: int = Field(..., ge=1)
    user_answer: Any = None


class QuizSubmitRequest(BaseModel):
    quiz_id: int = Field(..., ge=1)
    answers: List[QuizSubmitAnswer]


class QuizSubmitQuestionResult(BaseModel):
    question_id: int
    correct: Optional[bool] = None
    expected_answer: Any = None
    user_answer: Any = None


class QuizSubmitResponse(BaseModel):
    score: float = Field(..., ge=0)
    accuracy: float = Field(..., ge=0, le=1)
    per_question_result: List[QuizSubmitQuestionResult]
    feedback_text: str
