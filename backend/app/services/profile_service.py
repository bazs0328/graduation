from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db import models

DEFAULT_SESSION_ID = "default"
DEFAULT_ABILITY_LEVEL = "beginner"


def normalize_session_id(session_id: Optional[str]) -> str:
    value = (session_id or "").strip()
    return value or DEFAULT_SESSION_ID


def get_or_create_profile(db: Session, session_id: str) -> models.LearnerProfile:
    profile = (
        db.query(models.LearnerProfile)
        .filter(models.LearnerProfile.session_id == session_id)
        .first()
    )
    if profile:
        return profile

    profile = models.LearnerProfile(
        session_id=session_id,
        ability_level=DEFAULT_ABILITY_LEVEL,
        frustration_score=0,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def list_weak_concepts(db: Session, session_id: str) -> List[Dict[str, Any]]:
    stats = (
        db.query(models.ConceptStat)
        .filter(
            models.ConceptStat.session_id == session_id,
            models.ConceptStat.wrong_count > 0,
        )
        .order_by(models.ConceptStat.wrong_count.desc(), models.ConceptStat.concept.asc())
        .all()
    )
    results: List[Dict[str, Any]] = []
    for item in stats:
        total = (item.correct_count or 0) + (item.wrong_count or 0)
        wrong_rate = (item.wrong_count or 0) / total if total > 0 else 0.0
        results.append(
            {
                "concept": item.concept,
                "wrong_count": item.wrong_count or 0,
                "wrong_rate": round(wrong_rate, 4),
            }
        )
    return results


def get_last_quiz_summary(db: Session, session_id: str) -> Optional[Dict[str, Any]]:
    attempt = (
        db.query(models.QuizAttempt)
        .join(models.Quiz, models.QuizAttempt.quiz_id == models.Quiz.id)
        .filter(models.Quiz.session_id == session_id)
        .order_by(models.QuizAttempt.submitted_at.desc())
        .first()
    )
    if not attempt:
        return None
    if isinstance(attempt.summary_json, dict):
        return attempt.summary_json
    return attempt.summary_json


def build_profile_response(db: Session, session_id: Optional[str]) -> Dict[str, Any]:
    normalized_session = normalize_session_id(session_id)
    profile = get_or_create_profile(db, normalized_session)
    weak_concepts = list_weak_concepts(db, normalized_session)
    last_summary = get_last_quiz_summary(db, normalized_session)
    return {
        "ability_level": profile.ability_level,
        "frustration_score": profile.frustration_score or 0,
        "weak_concepts": weak_concepts,
        "last_quiz_summary": last_summary,
    }
