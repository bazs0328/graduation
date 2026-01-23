import io
from pathlib import Path
from typing import Dict, List

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from docx import Document as DocxDocument

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100


def extract_text(upload: UploadFile, data: bytes) -> str:
    filename = upload.filename or ""
    content_type = (upload.content_type or "").lower()
    ext = Path(filename).suffix.lower()

    if ext == ".pdf" or content_type == "application/pdf":
        return _extract_pdf(data)
    if ext == ".docx" or content_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return _extract_docx(data)
    if ext in {".md", ".markdown"} or content_type in {"text/markdown", "text/plain"}:
        return _extract_markdown(data)

    raise HTTPException(status_code=422, detail="Unsupported file type. Use PDF, DOCX, or Markdown.")


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
        text = "\n".join(pages).strip()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF parse failed: {exc}") from exc

    if not text:
        raise HTTPException(status_code=400, detail="PDF parse failed: empty text")

    return text


def _extract_docx(data: bytes) -> str:
    try:
        doc = DocxDocument(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        text = "\n".join(paragraphs).strip()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"DOCX parse failed: {exc}") from exc

    if not text:
        raise HTTPException(status_code=400, detail="DOCX parse failed: empty text")

    return text


def _extract_markdown(data: bytes) -> str:
    try:
        text = data.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Markdown decode failed: invalid UTF-8") from exc

    if not text:
        raise HTTPException(status_code=400, detail="Markdown parse failed: empty text")

    return text


def build_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Dict[str, int | str]]:
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Parsed text is empty")

    if chunk_size <= 0:
        raise HTTPException(status_code=400, detail="Chunk size must be positive")

    if overlap < 0:
        raise HTTPException(status_code=400, detail="Chunk overlap must be non-negative")

    if overlap >= chunk_size:
        raise HTTPException(status_code=400, detail="Chunk overlap must be smaller than chunk size")

    step = chunk_size - overlap
    chunks: List[Dict[str, int | str]] = []
    index = 0
    for start in range(0, len(cleaned), step):
        end = min(start + chunk_size, len(cleaned))
        chunk_text = cleaned[start:end]
        if chunk_text:
            chunks.append({"index": index, "text": chunk_text, "start": start, "end": end})
            index += 1

    return chunks