import re
from itertools import cycle
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import models
from app.services.index_manager import IndexManager
from app.services.llm.mock import MockLLM

DEFAULT_SESSION_ID = "default"
MAX_SNIPPET_LENGTH = 120


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
    llm: MockLLM,
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
        summary = llm.generate_answer("概括要点", snippet or "")
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


def generate_quiz(
    db: Session,
    index_manager: IndexManager,
    session_id: Optional[str],
    document_id: Optional[int],
    doc_ids: Optional[Sequence[int]],
    count: int,
    types: Sequence[str],
    focus_concepts: Optional[Sequence[str]],
) -> Dict[str, Any]:
    normalized_session = (session_id or "").strip() or DEFAULT_SESSION_ID
    resolved_doc_ids: Optional[Sequence[int]] = doc_ids or ([document_id] if document_id else None)
    if resolved_doc_ids:
        _ensure_documents_exist(db, resolved_doc_ids)

    chunks = _retrieve_chunks(db, index_manager, resolved_doc_ids, focus_concepts, count)
    chunk_cycle = cycle(chunks)
    type_cycle = cycle(types or ["single"])
    llm = MockLLM()

    quiz = models.Quiz(
        session_id=normalized_session,
        document_id=resolved_doc_ids[0] if resolved_doc_ids else None,
        difficulty_plan_json={"Easy": count, "Medium": 0, "Hard": 0},
    )
    db.add(quiz)
    db.flush()

    questions_payload: List[Dict[str, Any]] = []
    questions: List[models.QuizQuestion] = []
    for _ in range(count):
        chunk = next(chunk_cycle)
        question_type = next(type_cycle)
        question, payload = _build_question_payload(llm, question_type, "Easy", chunk)
        question.quiz_id = quiz.id
        db.add(question)
        questions.append(question)
        questions_payload.append(payload)

    db.flush()
    for question, payload in zip(questions, questions_payload):
        payload["question_id"] = question.id

    db.commit()

    return {"quiz_id": quiz.id, "questions": questions_payload}
