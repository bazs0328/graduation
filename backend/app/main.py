import os

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.db.session import get_db
from app.schemas.profile import ProfileResponse
from app.schemas.quiz_generate import QuizGenerateRequest, QuizGenerateResponse
from app.schemas.quiz_submit import QuizSubmitRequest, QuizSubmitResponse
from app.services.document_parser import build_chunks, extract_text
from app.services.embeddings import HashEmbedder
from app.services.index_manager import IndexManager
from app.services.llm.mock import MockLLM
from app.services.profile_service import build_profile_response
from app.services.quiz_service import QuizSubmitError, generate_quiz, submit_quiz
from .settings import load_settings

def _load_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
settings = load_settings()
index_manager = IndexManager(
    embedder=HashEmbedder(),
    index_path=settings.faiss_index_path,
    mapping_path=settings.faiss_mapping_path,
)
llm_client = MockLLM()
MAX_CONTEXT_LENGTH = 4000


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


@app.post("/index/rebuild")
def rebuild_index(db: Session = Depends(get_db)):
    return index_manager.rebuild(db)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)


@app.post("/search")
def search(request: SearchRequest, db: Session = Depends(get_db)):
    if not index_manager.is_ready():
        raise HTTPException(status_code=409, detail="Index not built. Call POST /index/rebuild first.")

    results = index_manager.search(request.query, request.top_k, db)
    return results


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)


@app.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if not index_manager.is_ready():
        raise HTTPException(status_code=409, detail="Index not built. Call POST /index/rebuild first.")

    results = index_manager.search(request.query, request.top_k, db)
    if not results:
        return {"answer": "资料中未找到相关内容", "sources": []}

    chunk_ids = [item["chunk_id"] for item in results]
    chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
    chunks_by_id = {chunk.id: (chunk.text or "") for chunk in chunks}

    query_text = request.query.strip().lower()
    matched_results = []
    for item in results:
        text = chunks_by_id.get(item["chunk_id"], "")
        if query_text and query_text in text.lower():
            matched_results.append(item)

    if not matched_results:
        return {"answer": "资料中未找到相关内容", "sources": []}

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
        return {"answer": "资料中未找到相关内容", "sources": []}

    answer = llm_client.generate_answer(request.query, context)
    sources = [
        {"chunk_id": item["chunk_id"], "document_id": item["document_id"], "score": item["score"]}
        for item in matched_results
    ]

    return {"answer": answer, "sources": sources}


def get_session_id(x_session_id: str | None = Header(default=None)) -> str:
    return (x_session_id or "").strip() or "default"


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
