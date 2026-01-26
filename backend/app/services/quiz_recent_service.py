from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db import models


def list_recent_quizzes(
    db: Session,
    session_id: str,
    limit: int,
) -> List[Dict[str, Any]]:
    attempts = (
        db.query(models.QuizAttempt)
        .join(models.Quiz, models.QuizAttempt.quiz_id == models.Quiz.id)
        .filter(models.Quiz.session_id == session_id)
        .order_by(models.QuizAttempt.submitted_at.desc())
        .limit(limit)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for attempt in attempts:
        quiz = attempt.quiz
        items.append(
            {
                "quiz_id": attempt.quiz_id,
                "submitted_at": attempt.submitted_at,
                "score": attempt.score,
                "accuracy": attempt.accuracy,
                "difficulty_plan": quiz.difficulty_plan_json if quiz else None,
                "summary": attempt.summary_json,
            }
        )
    return items
