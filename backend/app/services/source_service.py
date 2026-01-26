import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db import models

DEFAULT_PREVIEW_LEN = 120
MAX_PREVIEW_LEN = 500


@dataclass
class SourceResolveError(Exception):
    status_code: int
    message: str
    details: Optional[Dict[str, object]] = None


def _normalize_preview_len(value: Optional[int]) -> int:
    length = value or DEFAULT_PREVIEW_LEN
    length = max(20, min(length, MAX_PREVIEW_LEN))
    return length


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _build_preview(text: str, limit: int) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip()


def resolve_sources(
    db: Session,
    chunk_ids: Iterable[int],
    preview_len: Optional[int] = None,
) -> Tuple[List[Dict[str, object]], List[int]]:
    ids = [int(item) for item in chunk_ids if isinstance(item, int) or str(item).isdigit()]
    if not ids:
        raise SourceResolveError(422, "chunk_ids are required", {"chunk_ids": chunk_ids})

    preview_limit = _normalize_preview_len(preview_len)
    chunks = db.query(models.Chunk).filter(models.Chunk.id.in_(ids)).all()
    chunk_map = {chunk.id: chunk for chunk in chunks}
    document_ids = {chunk.document_id for chunk in chunks}
    documents = (
        db.query(models.Document)
        .filter(models.Document.id.in_(document_ids))
        .all()
        if document_ids
        else []
    )
    document_map = {doc.id: doc for doc in documents}

    items: List[Dict[str, object]] = []
    missing: List[int] = []
    for chunk_id in ids:
        chunk = chunk_map.get(chunk_id)
        if not chunk:
            missing.append(chunk_id)
            continue
        document = document_map.get(chunk.document_id)
        items.append(
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": document.filename if document else None,
                "text_preview": _build_preview(chunk.text or "", preview_limit),
            }
        )

    if not items:
        raise SourceResolveError(404, "Sources not found", {"missing_chunk_ids": missing})

    return items, missing
