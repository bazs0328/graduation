import os
import sys
import uuid

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.db import models
from app.db.session import SessionLocal


def main() -> None:
    session_id = f"verify-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        quiz = models.Quiz(
            session_id=session_id,
            document_id=None,
            difficulty_plan_json={"easy": 5},
        )
        db.add(quiz)
        db.flush()

        question = models.QuizQuestion(
            quiz_id=quiz.id,
            type="single",
            difficulty="Easy",
            stem="Sample question?",
            options_json=["A", "B", "C", "D"],
            answer_json={"choice": "A"},
            explanation="Sample explanation.",
            related_concept="sample",
            source_chunk_ids_json=[1],
        )
        db.add(question)

        profile = models.LearnerProfile(
            session_id=session_id,
            ability_level="beginner",
            frustration_score=0,
        )
        db.add(profile)

        db.commit()

        loaded_quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz.id).first()
        loaded_question = (
            db.query(models.QuizQuestion).filter(models.QuizQuestion.quiz_id == quiz.id).first()
        )
        loaded_profile = (
            db.query(models.LearnerProfile)
            .filter(models.LearnerProfile.session_id == session_id)
            .first()
        )

        print(
            "quiz_id={quiz_id} question_id={question_id} profile_id={profile_id} session_id={session_id}".format(
                quiz_id=loaded_quiz.id if loaded_quiz else None,
                question_id=loaded_question.id if loaded_question else None,
                profile_id=loaded_profile.id if loaded_profile else None,
                session_id=session_id,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
