import json
import logging
import os

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
import re

from app.db.models import Chunk, Document
from app.db.session import get_db
from app.schemas.profile import ProfileResponse
from app.schemas.quiz_generate import QuizGenerateRequest, QuizGenerateResponse
from app.schemas.quiz_recent import QuizRecentRequest, QuizRecentResponse
from app.schemas.quiz_submit import QuizSubmitRequest, QuizSubmitResponse
from app.schemas.research import (
    ResearchCreateRequest,
    ResearchCreateResponse,
    ResearchDetailResponse,
    ResearchEntryCreateRequest,
    ResearchEntryResponse,
    ResearchListResponse,
)
from app.schemas.source import SourceResolveRequest, SourceResolveResponse
from app.services.document_parser import build_chunks, extract_text
from app.services.doc_summary import SummaryCache, SummaryResult, build_context, generate_summary
from app.services.index_manager import IndexManager
from app.services.llm.mock import MockLLM
from app.services.provider_factory import build_embedder, build_llm_client
from app.services.profile_service import build_profile_response
from app.services.quiz_service import QuizSubmitError, generate_quiz, submit_quiz
from app.services.quiz_recent_service import list_recent_quizzes
from app.services.research_service import (
    ResearchError,
    add_research_entry,
    create_research_session,
    get_research_detail,
    list_research_sessions,
)
from app.services.source_service import SourceResolveError, resolve_sources
from app.services.tools import ToolRunError, build_tool_registry
from .settings import load_settings

def _load_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


app = FastAPI(docs_url="/api-docs", redoc_url="/api-redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
settings = load_settings()
index_manager = IndexManager(
    embedder=build_embedder(settings),
    index_path=settings.faiss_index_path,
    mapping_path=settings.faiss_mapping_path,
)
llm_client = build_llm_client(settings)
tool_registry = build_tool_registry(settings)
summary_cache = SummaryCache()
MAX_CONTEXT_LENGTH = 4000
logger = logging.getLogger(__name__)


@app.on_event("startup")
def load_index_on_startup():
    index_manager.load_if_exists()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/docs/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    text = extract_text(file, data)
    chunks = build_chunks(text)

    document = Document(
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
    )
    db.add(document)
    db.flush()

    chunk_rows = []
    for chunk in chunks:
        chunk_rows.append(
            Chunk(
                document_id=document.id,
                chunk_index=chunk["index"],
                text=chunk["text"],
                metadata_json={"start": chunk["start"], "end": chunk["end"]},
            )
        )

    db.add_all(chunk_rows)
    db.commit()

    return {
        "document_id": document.id,
        "chunk_count": len(chunk_rows),
        "filename": document.filename,
    }


@app.get("/docs/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_count = db.query(Chunk).filter(Chunk.document_id == doc_id).count()

    return {
        "id": document.id,
        "filename": document.filename,
        "content_type": document.content_type,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "chunk_count": chunk_count,
    }


@app.get("/docs")
def list_documents(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    total = db.query(func.count(Document.id)).scalar() or 0
    rows = (
        db.query(Document, func.count(Chunk.id))
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = []
    for document, chunk_count in rows:
        items.append(
            {
                "id": document.id,
                "filename": document.filename,
                "content_type": document.content_type,
                "created_at": document.created_at.isoformat() if document.created_at else None,
                "chunk_count": chunk_count,
            }
        )
    return {"total": total, "items": items, "limit": limit, "offset": offset}


@app.get("/docs/{doc_id}/chunks")
def list_document_chunks(
    doc_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    total = db.query(func.count(Chunk.id)).filter(Chunk.document_id == doc_id).scalar() or 0
    rows = (
        db.query(Chunk)
        .filter(Chunk.document_id == doc_id)
        .order_by(Chunk.chunk_index.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = []
    for chunk in rows:
        items.append(
            {
                "id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "metadata": chunk.metadata_json or {},
            }
        )
    return {
        "document_id": doc_id,
        "filename": document.filename,
        "total": total,
        "items": items,
        "limit": limit,
        "offset": offset,
    }


@app.delete("/docs/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()
    summary_cache.invalidate(doc_id)
    return {"status": "deleted", "document_id": doc_id}


@app.post("/index/rebuild")
def rebuild_index(db: Session = Depends(get_db)):
    return index_manager.rebuild(db)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)
    document_id: int | None = None


@app.post("/search")
def search(request: SearchRequest, db: Session = Depends(get_db)):
    if not index_manager.is_ready():
        raise HTTPException(status_code=409, detail="Index not built. Call POST /index/rebuild first.")

    results = index_manager.search(request.query, request.top_k, db, request.document_id)
    return results


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)
    document_id: int | None = None


class DocSummaryRequest(BaseModel):
    force: bool = False


class DocSummaryResponse(BaseModel):
    document_id: int
    summary: str
    keywords: list[str]
    questions: list[str]
    cached: bool


def _error_response(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "details": details or {}},
    )


@app.post("/docs/{doc_id}/summary", response_model=DocSummaryResponse)
def generate_doc_summary(
    doc_id: int,
    payload: DocSummaryRequest,
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        return _error_response(404, "DOC_NOT_FOUND", "Document not found", {"document_id": doc_id})

    if not payload.force:
        cached = summary_cache.get(doc_id)
        if cached:
            return DocSummaryResponse(
                document_id=doc_id,
                summary=cached["summary"],
                keywords=cached["keywords"],
                questions=cached["questions"],
                cached=True,
            )

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == doc_id)
        .order_by(Chunk.chunk_index.asc())
        .all()
    )
    if not chunks:
        return _error_response(409, "DOC_EMPTY", "Document has no chunks", {"document_id": doc_id})

    context = build_context([chunk.text for chunk in chunks])
    if not context:
        return _error_response(409, "DOC_EMPTY", "Document has no usable content", {"document_id": doc_id})

    try:
        result, trace = generate_summary(llm_client, context)
    except Exception as exc:
        logger.warning("LLM summary failed, falling back to MockLLM: %s", exc)
        result, trace = generate_summary(MockLLM(), context)
    summary_cache.set(doc_id, result)
    return DocSummaryResponse(
        document_id=doc_id,
        summary=result.summary,
        keywords=result.keywords,
        questions=result.questions,
        cached=False,
    )


@app.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if not index_manager.is_ready():
        raise HTTPException(status_code=409, detail="Index not built. Call POST /index/rebuild first.")

    forced_tool = _pick_forced_tool(request.query)
    if forced_tool and tool_registry and forced_tool in tool_registry:
        tool = tool_registry[forced_tool]
        expr = _extract_calc_expression(request.query) if forced_tool == "calc" else None
        if expr:
            try:
                output = tool.run({"expression": expr})
                return {
                    "answer": f"计算结果：{output}",
                    "structured": _build_fallback_structure(f"计算结果：{output}", []),
                    "sources": [],
                    "tool_traces": [
                        {"tool_name": forced_tool, "input": {"expression": expr}, "output": output, "error": None}
                    ],
                    "retrieval": {
                        "mode": "exact",
                        "reason": "forced_tool",
                        "suggestions": _build_suggestions(request.query),
                    },
                }
            except ToolRunError as exc:
                return {
                    "answer": f"计算失败：{exc}",
                    "structured": _build_fallback_structure(f"计算失败：{exc}", []),
                    "sources": [],
                    "tool_traces": [
                        {
                            "tool_name": forced_tool,
                            "input": {"expression": expr},
                            "output": None,
                            "error": str(exc),
                        }
                    ],
                    "retrieval": {
                        "mode": "exact",
                        "reason": "forced_tool",
                        "suggestions": _build_suggestions(request.query),
                    },
                }

    results = index_manager.search(request.query, request.top_k, db, request.document_id)
    doc_fallback_used = False
    if not results and request.document_id:
        results = _fallback_doc_results(request.document_id, request.query, request.top_k, db)
        doc_fallback_used = bool(results)
    if not results:
        if forced_tool and tool_registry:
            results = []
        else:
            suggestions = _build_suggestions(request.query)
            prompted_query = _build_prompted_query(request.query, "none", suggestions)
            try:
                answer = llm_client.generate_answer(prompted_query, "")
            except Exception as exc:
                logger.warning("LLM generate failed in /chat, falling back to MockLLM: %s", exc)
                answer = MockLLM().generate_answer(prompted_query, "")
            return {
                "answer": answer or "资料中未找到相关内容。",
                "structured": _build_fallback_structure(
                    answer or "资料中未找到相关内容。",
                    suggestions,
                ),
                "sources": [],
                "retrieval": {
                    "mode": "none",
                    "reason": "doc_filter_no_candidates" if request.document_id else "no_candidates",
                    "suggestions": suggestions,
                },
            }

    chunk_ids = [item["chunk_id"] for item in results]
    chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
    chunks_by_id = {chunk.id: (chunk.text or "") for chunk in chunks}

    query_tokens = _tokenize_query(request.query)
    matched_results = results[: min(len(results), request.top_k)]
    has_exact = False
    for item in matched_results:
        text = chunks_by_id.get(item["chunk_id"], "")
        score = _match_score(query_tokens, text)
        if score >= 0.34 or (score > 0 and len(query_tokens) <= 2):
            has_exact = True
            break

    match_mode = "exact" if has_exact else "semantic"

    context = ""
    if matched_results:
        context_parts = []
        total_len = 0
        for item in matched_results:
            text = chunks_by_id.get(item["chunk_id"], "")
            if not text:
                continue
            remaining = MAX_CONTEXT_LENGTH - total_len
            if remaining <= 0:
                break
            snippet = text[:remaining]
            context_parts.append(snippet)
            total_len += len(snippet)
            if total_len >= MAX_CONTEXT_LENGTH:
                break
        context = "\n\n".join(context_parts).strip()
        if not context:
            return {
                "answer": "资料中未找到相关内容",
                "structured": _build_fallback_structure("资料中未找到相关内容", suggestions),
                "sources": [],
            }

    suggestions = _build_suggestions(request.query)
    tool_traces: list[dict] = []
    prompted_query = _build_prompted_query(request.query, match_mode, suggestions)
    tools = list(tool_registry.values())
    try:
        if tools:
            answer, tool_traces = llm_client.generate_answer_with_tools(
                prompted_query,
                context,
                tools,
                settings.llm_tool_max_calls,
                forced_tool=forced_tool,
            )
        else:
            answer = llm_client.generate_answer(prompted_query, context)
    except Exception as exc:
        logger.warning("LLM generate failed in /chat, falling back to MockLLM: %s", exc)
        fallback = MockLLM()
        if tools:
            answer, tool_traces = fallback.generate_answer_with_tools(
                prompted_query,
                context,
                tools,
                settings.llm_tool_max_calls,
                forced_tool=forced_tool,
            )
        else:
            answer = fallback.generate_answer(prompted_query, context)
    sources = [
        {
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "score": item["score"],
            "match_mode": match_mode,
        }
        for item in matched_results
    ]
    structured = _build_structured_answer(
        llm_client=llm_client,
        query=request.query,
        match_mode=match_mode,
        answer=answer,
        suggestions=suggestions,
        sources=matched_results,
        chunks_by_id=chunks_by_id,
    )
    if structured and structured.get("conclusion"):
        answer = structured["conclusion"]

    if doc_fallback_used:
        retrieval_reason = (
            "doc_filter_fallback_exact" if match_mode == "exact" else "doc_filter_fallback_semantic"
        )
    else:
        retrieval_reason = "exact_match" if match_mode == "exact" else "semantic_fallback"
    return {
        "answer": answer,
        "structured": structured,
        "sources": sources,
        "tool_traces": tool_traces,
        "retrieval": {
            "mode": match_mode,
            "reason": retrieval_reason,
            "suggestions": suggestions,
        },
    }


def _pick_forced_tool(query: str) -> str | None:
    trimmed = (query or "").strip()
    lowered = trimmed.lower()
    if lowered.startswith("calc:") or trimmed.startswith("计算"):
        return "calc"
    return None


def _build_structured_answer(
    llm_client,
    query: str,
    match_mode: str,
    answer: str,
    suggestions: list[str],
    sources: list[dict],
    chunks_by_id: dict[int, str],
) -> dict:
    if not answer:
        return _build_fallback_structure("资料中未找到相关内容", suggestions)
    if not sources:
        return _build_fallback_structure(answer, suggestions)

    prompt = _build_structured_prompt(query, match_mode, suggestions, sources, chunks_by_id)
    try:
        raw = llm_client.generate_answer(f"RAW_JSON:{prompt}", "")
    except Exception:
        return _build_fallback_structure(answer, suggestions, sources, chunks_by_id)
    parsed = _parse_structured_json(raw, allowed_chunk_ids={item["chunk_id"] for item in sources})
    if not parsed:
        return _build_fallback_structure(answer, suggestions, sources, chunks_by_id)
    if not parsed.get("next_steps"):
        parsed["next_steps"] = suggestions[:3]
    if not parsed.get("conclusion"):
        parsed["conclusion"] = answer
    if not parsed.get("evidence"):
        parsed["evidence"] = _build_evidence_fallback(sources, chunks_by_id)
    return parsed


def _build_structured_prompt(
    query: str,
    match_mode: str,
    suggestions: list[str],
    sources: list[dict],
    chunks_by_id: dict[int, str],
) -> str:
    source_lines = []
    for item in sources[:6]:
        chunk_id = item["chunk_id"]
        text = (chunks_by_id.get(chunk_id, "") or "")[:160].replace("\n", " ")
        source_lines.append(f"- chunk_id={chunk_id}: {text}")
    source_text = "\n".join(source_lines)
    suggestion_text = "；".join(suggestions[:3]) if suggestions else ""
    return (
        "请根据资料片段与问题，输出结构化回答（只输出JSON，不要其他文本）。\n"
        "JSON结构：\n"
        "{"
        "\"conclusion\":\"结论（1-2句）\","
        "\"evidence\":[{\"chunk_id\":8,\"quote\":\"引用资料原句片段\"}],"
        "\"reasoning\":\"推理过程（1-3句）\","
        "\"next_steps\":[\"下一步建议1\",\"下一步建议2\"]"
        "}\n"
        "要求：\n"
        "1) evidence 的 chunk_id 必须来自提供的片段列表；\n"
        "2) reasoning 必须基于证据，不要引入资料外信息；\n"
        "3) 若资料不足，conclusion 需明确说明并给出 next_steps；\n"
        "4) 全部使用中文。\n"
        f"问题：{query}\n"
        f"检索模式：{match_mode}\n"
        f"改写建议：{suggestion_text}\n"
        "资料片段：\n"
        f"{source_text}\n"
    )


def _parse_structured_json(raw: str, allowed_chunk_ids: set[int]) -> dict | None:
    if not raw:
        return None
    raw = raw.strip()
    payload = None
    if raw.startswith("{") and raw.endswith("}"):
        payload = raw
    else:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            payload = match.group(0)
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    conclusion = (data.get("conclusion") or "").strip()
    reasoning = (data.get("reasoning") or "").strip()
    next_steps = data.get("next_steps") or []
    if isinstance(next_steps, str):
        next_steps = [next_steps]
    evidence = data.get("evidence") or []
    if isinstance(evidence, dict):
        evidence = [evidence]
    cleaned_evidence = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("chunk_id")
        quote = (item.get("quote") or "").strip()
        if not isinstance(chunk_id, int) or chunk_id not in allowed_chunk_ids:
            continue
        if not quote:
            continue
        cleaned_evidence.append({"chunk_id": chunk_id, "quote": quote})
    return {
        "conclusion": conclusion,
        "evidence": cleaned_evidence,
        "reasoning": reasoning,
        "next_steps": [step for step in next_steps if isinstance(step, str) and step.strip()],
    }


def _build_evidence_fallback(sources: list[dict], chunks_by_id: dict[int, str]) -> list[dict]:
    evidence = []
    for item in sources[:3]:
        chunk_id = item["chunk_id"]
        text = (chunks_by_id.get(chunk_id, "") or "").strip()
        if not text:
            continue
        evidence.append({"chunk_id": chunk_id, "quote": text[:120]})
    return evidence


def _build_fallback_structure(
    conclusion: str,
    suggestions: list[str],
    sources: list[dict] | None = None,
    chunks_by_id: dict[int, str] | None = None,
) -> dict:
    evidence = []
    if sources and chunks_by_id:
        evidence = _build_evidence_fallback(sources, chunks_by_id)
    return {
        "conclusion": conclusion,
        "evidence": evidence,
        "reasoning": "",
        "next_steps": suggestions[:3],
    }


def _fallback_doc_results(
    document_id: int,
    query: str,
    top_k: int,
    db: Session,
) -> list[dict]:
    query_tokens = _tokenize_query(query)
    if not query_tokens:
        return []
    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
        .all()
    )
    scored: list[tuple[float, Chunk]] = []
    for chunk in chunks:
        text = chunk.text or ""
        score = _match_score(query_tokens, text)
        if score > 0:
            scored.append((score, chunk))
    if not scored:
        return []
    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict] = []
    for score, chunk in scored[:top_k]:
        preview = (chunk.text or "")[:200]
        results.append(
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "score": score,
                "text_preview": preview,
                "metadata": chunk.metadata_json,
            }
        )
    return results


def _extract_calc_expression(query: str) -> str | None:
    if not query:
        return None
    trimmed = query.strip()
    lowered = trimmed.lower()
    if lowered.startswith("calc:"):
        return trimmed.split(":", 1)[1].strip()
    if trimmed.startswith("计算"):
        return trimmed[2:].strip()
    return None


STOPWORDS = {
    "的",
    "了",
    "吗",
    "呢",
    "和",
    "或",
    "以及",
    "就是",
    "如何",
    "怎么",
    "什么",
    "哪些",
    "请",
    "是否",
    "能否",
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
}


def _tokenize_query(text: str) -> list[str]:
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,}", text.lower())
    cleaned = [token for token in tokens if token and token not in STOPWORDS]
    return cleaned


def _match_score(query_tokens: list[str], text: str) -> float:
    if not query_tokens or not text:
        return 0.0
    text_lower = text.lower()
    common = [token for token in query_tokens if token in text_lower]
    return len(common) / max(len(query_tokens), 1)


def _build_suggestions(query: str) -> list[str]:
    tokens = _tokenize_query(query)
    if not tokens:
        return []
    keywords = []
    for token in tokens:
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= 3:
            break
    if not keywords:
        return []
    suggestions = []
    if len(keywords) == 1:
        suggestions.append(f"解释一下 {keywords[0]} 的核心概念")
        suggestions.append(f"{keywords[0]} 的关键结论有哪些？")
        suggestions.append(f"{keywords[0]} 的常见问题与误区")
    else:
        joined = "、".join(keywords)
        suggestions.append(f"概括 {joined} 的重点内容")
        suggestions.append(f"{joined} 之间的关系是什么？")
        suggestions.append(f"基于资料解释 {keywords[0]}")
    return suggestions


def _build_prompted_query(query: str, match_mode: str, suggestions: list[str]) -> str:
    if match_mode == "exact":
        return query
    suggestion_text = "；".join(suggestions[:3]) if suggestions else ""
    return (
        "请仅基于提供的资料回答，若资料不足请明确说明不足，并给出2-3条可改写的问题建议。\n"
        f"问题：{query}\n"
        f"建议示例：{suggestion_text}"
    )


@app.post("/sources/resolve", response_model=SourceResolveResponse)
def resolve_source_chunks(
    request: SourceResolveRequest,
    db: Session = Depends(get_db),
):
    try:
        items, missing = resolve_sources(db, request.chunk_ids, request.preview_len)
        return {"items": items, "missing_chunk_ids": missing}
    except SourceResolveError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "details": exc.details},
        )


def get_session_id(x_session_id: str | None = Header(default=None)) -> str:
    return (x_session_id or "").strip() or "default"


def require_session_id(x_session_id: str | None) -> str:
    trimmed = (x_session_id or "").strip()
    if not trimmed:
        raise ResearchError(400, "X-Session-Id is required", {"header": "X-Session-Id"})
    return trimmed


@app.post("/research", response_model=ResearchCreateResponse)
def create_research(
    request: ResearchCreateRequest,
    db: Session = Depends(get_db),
    x_session_id: str | None = Header(default=None),
):
    try:
        session_id = require_session_id(x_session_id)
        research = create_research_session(db, session_id, request.title, request.summary)
        return {
            "research_id": research.id,
            "session_id": research.session_id,
            "title": research.title,
            "summary": research.summary,
            "created_at": research.created_at,
            "updated_at": research.updated_at,
        }
    except ResearchError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "details": exc.details},
        )


@app.post("/research/{research_id}/entries", response_model=ResearchEntryResponse)
def append_research_entry(
    research_id: int,
    request: ResearchEntryCreateRequest,
    db: Session = Depends(get_db),
    x_session_id: str | None = Header(default=None),
):
    try:
        session_id = require_session_id(x_session_id)
        entry = add_research_entry(
            db,
            session_id=session_id,
            research_id=research_id,
            entry_type=request.entry_type,
            content=request.content,
            tool_traces=request.tool_traces,
            sources=request.sources,
        )
        return {
            "entry_id": entry.id,
            "research_id": entry.research_id,
            "entry_type": entry.entry_type,
            "content": entry.content,
            "tool_traces": entry.tool_traces_json,
            "sources": entry.sources_json,
            "created_at": entry.created_at,
        }
    except ResearchError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "details": exc.details},
        )


@app.get("/research", response_model=ResearchListResponse)
def list_research(
    db: Session = Depends(get_db),
    x_session_id: str | None = Header(default=None),
):
    try:
        session_id = require_session_id(x_session_id)
        items = list_research_sessions(db, session_id)
        return {
            "items": [
                {
                    "research_id": research.id,
                    "title": research.title,
                    "summary": research.summary,
                    "entry_count": count,
                    "created_at": research.created_at,
                    "updated_at": research.updated_at,
                }
                for research, count in items
            ]
        }
    except ResearchError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "details": exc.details},
        )


@app.get("/research/{research_id}", response_model=ResearchDetailResponse)
def research_detail(
    research_id: int,
    db: Session = Depends(get_db),
    x_session_id: str | None = Header(default=None),
):
    try:
        session_id = require_session_id(x_session_id)
        research, entries = get_research_detail(db, session_id, research_id)
        return {
            "research_id": research.id,
            "session_id": research.session_id,
            "title": research.title,
            "summary": research.summary,
            "created_at": research.created_at,
            "updated_at": research.updated_at,
            "entries": [
                {
                    "entry_id": entry.id,
                    "research_id": entry.research_id,
                    "entry_type": entry.entry_type,
                    "content": entry.content,
                    "tool_traces": entry.tool_traces_json,
                    "sources": entry.sources_json,
                    "created_at": entry.created_at,
                }
                for entry in entries
            ],
        }
    except ResearchError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "details": exc.details},
        )


@app.get("/profile/me", response_model=ProfileResponse)
def get_profile_me(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    return build_profile_response(db, session_id)


@app.post("/quiz/generate", response_model=QuizGenerateResponse)
def quiz_generate(
    request: QuizGenerateRequest,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    return generate_quiz(
        db=db,
        index_manager=index_manager,
        session_id=session_id,
        document_id=request.document_id,
        doc_ids=request.doc_ids,
        count=request.count,
        types=[item.value for item in request.types],
        focus_concepts=request.focus_concepts,
        llm_client=llm_client,
    )


@app.post("/quiz/submit", response_model=QuizSubmitResponse)
def quiz_submit(
    request: QuizSubmitRequest,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    try:
        return submit_quiz(
            db=db,
            quiz_id=request.quiz_id,
            answers=request.answers,
            session_id=session_id,
        )
    except QuizSubmitError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "details": exc.details},
        )


@app.post("/quizzes/recent", response_model=QuizRecentResponse)
def quizzes_recent(
    request: QuizRecentRequest,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    items = list_recent_quizzes(db, session_id, request.limit)
    return {"items": items}
