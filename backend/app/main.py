from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.db.session import get_db
from app.services.document_parser import build_chunks, extract_text
from app.services.embeddings import HashEmbedder
from app.services.index_manager import IndexManager
from .settings import load_settings

app = FastAPI()
settings = load_settings()
index_manager = IndexManager(
    embedder=HashEmbedder(),
    index_path=settings.faiss_index_path,
    mapping_path=settings.faiss_mapping_path,
)


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
