from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WeakConcept(BaseModel):
    concept: str
    wrong_count: int
    wrong_rate: float


class ProfileResponse(BaseModel):
    ability_level: Optional[str] = None
    frustration_score: int = 0
    weak_concepts: List[WeakConcept] = Field(default_factory=list)
    last_quiz_summary: Optional[Dict[str, Any]] = None
