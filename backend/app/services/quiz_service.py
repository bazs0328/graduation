import logging
import re
from datetime import datetime
from itertools import cycle
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import models
from app.services.index_manager import IndexManager
from app.services.profile_service import (
    build_difficulty_plan,
    get_last_quiz_summary,
    get_or_create_profile,
)
from app.services.llm.base import LLMClient
from app.services.llm.mock import MockLLM

DEFAULT_SESSION_ID = "default"
MAX_SNIPPET_LENGTH = 120
logger = logging.getLogger(__name__)


class QuizSubmitError(Exception):
    def __init__(self, status_code: int, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details


def _normalize_session_id(session_id: Optional[str]) -> str:
    value = (session_id or "").strip()
    return value or DEFAULT_SESSION_ID


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_snippet(text: str) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= MAX_SNIPPET_LENGTH:
        return cleaned
    return cleaned[:MAX_SNIPPET_LENGTH].rstrip()


def _derive_concept(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return "general"
    tokens = re.findall(r"[A-Za-z0-9_\\u4e00-\\u9fff]+", cleaned)
    if not tokens:
        return "general"
    return tokens[0][:50]


def _ensure_documents_exist(db: Session, doc_ids: Sequence[int]) -> None:
    if not doc_ids:
        return
    found = db.query(models.Document.id).filter(models.Document.id.in_(doc_ids)).all()
    if not found:
        raise HTTPException(status_code=404, detail="Document not found")


def _retrieve_chunks(
    db: Session,
    index_manager: IndexManager,
    doc_ids: Optional[Sequence[int]],
    focus_concepts: Optional[Sequence[str]],
    count: int,
) -> List[models.Chunk]:
    if not index_manager.is_ready():
        raise HTTPException(status_code=409, detail="Index not built. Call POST /index/rebuild first.")

    if focus_concepts:
        chunk_ids: List[int] = []
        for concept in focus_concepts:
            if not concept:
                continue
            results = index_manager.search(concept, top_k=max(count, 5), db=db)
            for item in results:
                if doc_ids and item["document_id"] not in doc_ids:
                    continue
                chunk_ids.append(item["chunk_id"])
        if not chunk_ids:
            raise HTTPException(status_code=409, detail="Insufficient data for quiz generation.")
        unique_chunk_ids = list(dict.fromkeys(chunk_ids))
        chunks = db.query(models.Chunk).filter(models.Chunk.id.in_(unique_chunk_ids)).all()
        chunks_by_id = {chunk.id: chunk for chunk in chunks}
        ordered_chunks = [chunks_by_id[cid] for cid in unique_chunk_ids if cid in chunks_by_id]
        if not ordered_chunks:
            raise HTTPException(status_code=409, detail="Insufficient data for quiz generation.")
        return ordered_chunks

    query = db.query(models.Chunk)
    if doc_ids:
        query = query.filter(models.Chunk.document_id.in_(doc_ids))
    chunks = query.order_by(models.Chunk.id.asc()).limit(max(count, 1)).all()
    if not chunks:
        raise HTTPException(status_code=409, detail="Insufficient data for quiz generation.")
    return chunks


def _build_question_payload(
    llm: LLMClient,
    question_type: str,
    difficulty: str,
    chunk: models.Chunk,
) -> Tuple[models.QuizQuestion, Dict[str, Any]]:
    snippet = _extract_snippet(chunk.text or "")
    related_concept = _derive_concept(chunk.text or "")
    explanation = f"依据资料片段：{snippet}" if snippet else None
    options: Optional[List[str]] = None
    answer: Dict[str, Any]

    if question_type == "single":
        options = [
            snippet or "资料片段为空",
            "无关选项一",
            "无关选项二",
            "无关选项三",
        ]
        answer = {"choice": "A"}
        stem = "以下哪一项在资料中出现？"
    elif question_type == "judge":
        answer = {"value": True}
        stem = f"判断正误：{snippet}" if snippet else "判断正误：资料片段为空"
    else:
        summary = _safe_llm_generate(llm, "概括要点", snippet or "")
        answer = {"reference_answer": summary}
        stem = f"简要概括以下内容的要点：{snippet}" if snippet else "简要概括以下内容的要点："

    question = models.QuizQuestion(
        quiz_id=0,
        type=question_type,
        difficulty=difficulty,
        stem=stem,
        options_json=options,
        answer_json=answer,
        explanation=explanation,
        related_concept=related_concept,
        source_chunk_ids_json=[chunk.id],
    )

    payload = {
        "type": question_type,
        "difficulty": difficulty,
        "stem": stem,
        "options": options,
        "answer": answer,
        "explanation": explanation,
        "source_chunk_ids": [chunk.id],
        "related_concept": related_concept,
    }
    return question, payload


def _safe_llm_generate(llm: LLMClient, query: str, context: str) -> str:
    try:
        return llm.generate_answer(query, context)
    except Exception as exc:
        logger.warning("LLM generate failed, falling back to MockLLM: %s", exc)
        try:
            return MockLLM().generate_answer(query, context)
        except Exception:
            logger.exception("MockLLM fallback failed.")
            raise


def generate_quiz(
    db: Session,
    index_manager: IndexManager,
    session_id: Optional[str],
    document_id: Optional[int],
    doc_ids: Optional[Sequence[int]],
    count: int,
    types: Sequence[str],
    focus_concepts: Optional[Sequence[str]],
    llm_client: Optional[LLMClient] = None,
) -> Dict[str, Any]:
    normalized_session = (session_id or "").strip() or DEFAULT_SESSION_ID
    resolved_doc_ids: Optional[Sequence[int]] = doc_ids or ([document_id] if document_id else None)
    if resolved_doc_ids:
        _ensure_documents_exist(db, resolved_doc_ids)

    profile = get_or_create_profile(db, normalized_session)
    last_summary = get_last_quiz_summary(db, normalized_session)
    recommendation = None
    if isinstance(last_summary, dict):
        recommendation = last_summary.get("next_quiz_recommendation")
    difficulty_plan = build_difficulty_plan(
        ability_level=profile.ability_level,
        frustration_score=profile.frustration_score or 0,
        count=count,
        recommendation=recommendation,
    )

    chunks = _retrieve_chunks(db, index_manager, resolved_doc_ids, focus_concepts, count)
    chunk_cycle = cycle(chunks)
    type_cycle = cycle(types or ["single"])
    llm = llm_client or MockLLM()

    quiz = models.Quiz(
        session_id=normalized_session,
        document_id=resolved_doc_ids[0] if resolved_doc_ids else None,
        difficulty_plan_json=difficulty_plan,
    )
    db.add(quiz)
    db.flush()

    questions_payload: List[Dict[str, Any]] = []
    questions: List[models.QuizQuestion] = []
    difficulty_sequence = (
        ["Easy"] * difficulty_plan.get("Easy", 0)
        + ["Medium"] * difficulty_plan.get("Medium", 0)
        + ["Hard"] * difficulty_plan.get("Hard", 0)
    )
    difficulty_cycle = cycle(difficulty_sequence or ["Easy"])
    for _ in range(count):
        chunk = next(chunk_cycle)
        question_type = next(type_cycle)
        difficulty = next(difficulty_cycle)
        question, payload = _build_question_payload(llm, question_type, difficulty, chunk)
        question.quiz_id = quiz.id
        db.add(question)
        questions.append(question)
        questions_payload.append(payload)

    db.flush()
    for question, payload in zip(questions, questions_payload):
        payload["question_id"] = question.id

    db.commit()

    return {"quiz_id": quiz.id, "difficulty_plan": difficulty_plan, "questions": questions_payload}


def _coerce_choice(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        value = value.get("choice")
    if isinstance(value, str):
        value = value.strip().upper()
        return value or None
    return None


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return None


def _normalize_answers(raw_answers: Iterable[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in raw_answers:
        if isinstance(item, dict):
            question_id = item.get("question_id")
            user_answer = item.get("user_answer")
        else:
            question_id = getattr(item, "question_id", None)
            user_answer = getattr(item, "user_answer", None)
        normalized.append({"question_id": question_id, "user_answer": user_answer})
    return normalized


def _normalize_concept(value: Optional[str]) -> str:
    cleaned = (value or "").strip()
    return cleaned or "general"


def _get_or_create_concept_stat(db: Session, session_id: str, concept: str) -> models.ConceptStat:
    stat = (
        db.query(models.ConceptStat)
        .filter(
            models.ConceptStat.session_id == session_id,
            models.ConceptStat.concept == concept,
        )
        .first()
    )
    if stat:
        return stat
    stat = models.ConceptStat(
        session_id=session_id,
        concept=concept,
        correct_count=0,
        wrong_count=0,
        last_seen=datetime.utcnow(),
    )
    db.add(stat)
    return stat


def submit_quiz(
    db: Session,
    quiz_id: int,
    answers: Iterable[Any],
    session_id: Optional[str],
) -> Dict[str, Any]:
    normalized_session = _normalize_session_id(session_id)
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise QuizSubmitError(404, "Quiz not found", {"quiz_id": quiz_id})
    if quiz.session_id != normalized_session:
        raise QuizSubmitError(
            403,
            "Session mismatch for quiz",
            {"quiz_id": quiz_id, "session_id": normalized_session},
        )

    questions = (
        db.query(models.QuizQuestion)
        .filter(models.QuizQuestion.quiz_id == quiz_id)
        .order_by(models.QuizQuestion.id.asc())
        .all()
    )
    if not questions:
        raise QuizSubmitError(404, "Quiz questions not found", {"quiz_id": quiz_id})

    normalized_answers = _normalize_answers(answers or [])
    if not normalized_answers:
        raise QuizSubmitError(422, "Answers are required", {"quiz_id": quiz_id})

    seen_ids: set[int] = set()
    for item in normalized_answers:
        question_id = item.get("question_id")
        if not isinstance(question_id, int) or question_id <= 0:
            raise QuizSubmitError(422, "Invalid question_id in answers", {"question_id": question_id})
        if question_id in seen_ids:
            raise QuizSubmitError(422, "Duplicate question_id in answers", {"question_id": question_id})
        seen_ids.add(question_id)

    question_ids = {question.id for question in questions}
    submitted_ids = set(seen_ids)
    missing_ids = sorted(question_ids - submitted_ids)
    extra_ids = sorted(submitted_ids - question_ids)
    if missing_ids or extra_ids:
        raise QuizSubmitError(
            422,
            "Answers must match quiz questions",
            {"missing_question_ids": missing_ids, "extra_question_ids": extra_ids},
        )

    answers_by_id = {item["question_id"]: item["user_answer"] for item in normalized_answers}
    per_question_result: List[Dict[str, Any]] = []
    correct_count = 0
    objective_total = 0
    has_short = False
    concept_stats_cache: Dict[str, models.ConceptStat] = {}
    session_correct_count = 0
    session_wrong_count = 0
    objective_seen = 0
    wrong_first_five = 0
    wrong_concepts: Dict[str, int] = {}

    for question in questions:
        user_answer = answers_by_id.get(question.id)
        expected_answer = question.answer_json
        correct: Optional[bool] = None

        if question.type == "single":
            objective_total += 1
            expected_choice = _coerce_choice(expected_answer)
            user_choice = _coerce_choice(user_answer)
            correct = user_choice is not None and expected_choice is not None and user_choice == expected_choice
            if correct:
                correct_count += 1
        elif question.type == "judge":
            objective_total += 1
            expected_value = _coerce_bool(expected_answer)
            user_value = _coerce_bool(user_answer)
            correct = user_value is not None and expected_value is not None and user_value == expected_value
            if correct:
                correct_count += 1
        else:
            has_short = True

        if correct is not None:
            concept = _normalize_concept(question.related_concept)
            stat = concept_stats_cache.get(concept)
            if not stat:
                stat = _get_or_create_concept_stat(db, normalized_session, concept)
                concept_stats_cache[concept] = stat
            if correct:
                stat.correct_count = (stat.correct_count or 0) + 1
                session_correct_count += 1
            else:
                stat.wrong_count = (stat.wrong_count or 0) + 1
                session_wrong_count += 1
                wrong_concepts[concept] = wrong_concepts.get(concept, 0) + 1
            stat.last_seen = datetime.utcnow()
            if objective_seen < 5:
                if not correct:
                    wrong_first_five += 1
                objective_seen += 1

        per_question_result.append(
            {
                "question_id": question.id,
                "correct": correct,
                "expected_answer": expected_answer,
                "user_answer": user_answer,
            }
        )

    accuracy = round(correct_count / objective_total, 4) if objective_total > 0 else 0.0
    score = float(correct_count)

    feedback_parts = []
    if objective_total > 0:
        feedback_parts.append(f"客观题正确 {correct_count}/{objective_total}。")
    else:
        feedback_parts.append("本次没有可评分的客观题。")
    if has_short:
        feedback_parts.append("简答题请参考参考答案自评。")
    overhard = False
    if objective_total > 0:
        if accuracy < 0.3:
            overhard = True
        elif objective_seen >= 5 and wrong_first_five >= 4:
            overhard = True

    if overhard:
        focus_concept = None
        if wrong_concepts:
            focus_concept = sorted(wrong_concepts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        if focus_concept:
            feedback_parts.append(f"本次题目偏难，别灰心，建议先复习：{focus_concept}。")
        else:
            feedback_parts.append("本次题目偏难，别灰心，建议先复习基础概念。")
        feedback_parts.append("下次会优先出简单题，逐步加难。")

    feedback_text = " ".join(feedback_parts)

    summary_json = {
        "quiz_id": quiz_id,
        "score": score,
        "accuracy": accuracy,
        "objective_total": objective_total,
        "correct_count": correct_count,
        "feedback_text": feedback_text,
        "per_question_result": per_question_result,
    }
    if overhard:
        summary_json["next_quiz_recommendation"] = "easy_first"

    attempt = models.QuizAttempt(
        quiz_id=quiz.id,
        score=score,
        accuracy=accuracy,
        summary_json=summary_json,
    )
    db.add(attempt)

    profile = (
        db.query(models.LearnerProfile)
        .filter(models.LearnerProfile.session_id == normalized_session)
        .first()
    )
    if not profile:
        profile = models.LearnerProfile(
            session_id=normalized_session,
            ability_level="beginner",
            frustration_score=0,
        )
        db.add(profile)

    if objective_total > 0:
        if accuracy < 0.5:
            profile.ability_level = "beginner"
        elif accuracy < 0.8:
            profile.ability_level = "intermediate"
        else:
            profile.ability_level = "advanced"

    if session_wrong_count >= 3 or (objective_total > 0 and accuracy < 0.3):
        profile.frustration_score = min((profile.frustration_score or 0) + 1, 10)
    elif session_correct_count > 0:
        profile.frustration_score = max((profile.frustration_score or 0) - 1, 0)
    profile.last_updated = datetime.utcnow()
    db.commit()

    return {
        "score": score,
        "accuracy": accuracy,
        "per_question_result": per_question_result,
        "feedback_text": feedback_text,
    }
