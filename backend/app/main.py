from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.db.session import get_db
from app.services.document_parser import build_chunks, extract_text
from .settings import load_settings

app = FastAPI()
settings = load_settings()


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
