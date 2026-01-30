import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import faiss
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Chunk
from app.services.embeddings import Embedder

logger = logging.getLogger("uvicorn.error")
PREVIEW_LENGTH = 200


class IndexManager:
    def __init__(self, embedder: Embedder, index_path: str, mapping_path: str):
        self.embedder = embedder
        self.dim = embedder.dim
        self.index_path = Path(index_path)
        self.mapping_path = Path(mapping_path)
        self.index = None
        self.mapping: List[Dict[str, Any]] = []
        self._rebuild_lock = threading.Lock()
        self._last_rebuild_at = 0.0

    def load_if_exists(self) -> bool:
        if not (self.index_path.exists() and self.mapping_path.exists()):
            logger.warning("FAISS index not found. Call POST /index/rebuild.")
            return False

        self.index = faiss.read_index(str(self.index_path))
        with self.mapping_path.open("r", encoding="utf-8") as handle:
            self.mapping = json.load(handle)

        if self.index.d != self.dim:
            logger.warning(
                "FAISS index dim %s does not match embedder dim %s.",
                self.index.d,
                self.dim,
            )
        if self.index.ntotal != len(self.mapping):
            logger.warning(
                "FAISS index count %s does not match mapping count %s.",
                self.index.ntotal,
                len(self.mapping),
            )
        logger.info(
            "Loaded FAISS index from %s (chunks=%s)",
            self.index_path,
            self.index.ntotal,
        )
        return True

    def needs_rebuild(self, db: Session) -> bool:
        chunk_total = db.query(func.count(Chunk.id)).scalar() or 0
        if self.index is None:
            return True
        if len(self.mapping) != chunk_total:
            return True
        return False

    def rebuild(self, db: Session) -> Dict[str, Any]:
        chunks = db.query(Chunk).order_by(Chunk.id).all()
        texts = [chunk.text for chunk in chunks]
        vectors = self.embedder.embed_texts(texts)

        index = faiss.IndexFlatL2(self.dim)
        if len(chunks) > 0:
            index.add(vectors)

        mapping: List[Dict[str, Any]] = []
        for chunk in chunks:
            mapping.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                }
            )

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.index_path))
        with self.mapping_path.open("w", encoding="utf-8") as handle:
            json.dump(mapping, handle, ensure_ascii=True)

        self.index = index
        self.mapping = mapping

        return {
            "chunk_total": len(mapping),
            "dim": self.dim,
            "index_path": str(self.index_path),
        }

    def rebuild_with_lock(
        self,
        db: Session,
        reason: str,
        debounce_seconds: float = 0.0,
        force: bool = False,
    ) -> Dict[str, Any] | None:
        if self._rebuild_lock.locked():
            logger.info("Skip index rebuild; already running (%s).", reason)
            return None
        now = time.monotonic()
        if not force and debounce_seconds > 0:
            if (now - self._last_rebuild_at) < debounce_seconds:
                logger.info("Skip index rebuild; debounce active (%s).", reason)
                return None
        if not self._rebuild_lock.acquire(blocking=False):
            logger.info("Skip index rebuild; lock unavailable (%s).", reason)
            return None
        try:
            result = self.rebuild(db)
            self._last_rebuild_at = time.monotonic()
            logger.info("Index rebuilt (%s).", reason)
            return result
        except Exception:
            logger.exception("Index rebuild failed (%s).", reason)
            return None
        finally:
            self._rebuild_lock.release()

    def is_ready(self) -> bool:
        return self.index is not None

    def search(
        self,
        query: str,
        top_k: int,
        db: Session,
        document_id: int | None = None,
    ) -> List[Dict[str, Any]]:
        if self.index is None:
            return []

        if self.index.ntotal == 0:
            return []

        vectors = self.embedder.embed_texts([query])
        if document_id is not None:
            k = min(max(top_k * 5, top_k), self.index.ntotal)
        else:
            k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(vectors, k)

        ordered_indices = [int(idx) for idx in indices[0] if idx >= 0]
        chunk_ids = []
        for idx in ordered_indices:
            if idx < len(self.mapping):
                chunk_ids.append(self.mapping[idx]["chunk_id"])

        if not chunk_ids:
            return []

        chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
        chunks_by_id = {chunk.id: chunk for chunk in chunks}

        results: List[Dict[str, Any]] = []
        for rank, idx in enumerate(ordered_indices):
            if idx >= len(self.mapping):
                continue
            mapping = self.mapping[idx]
            chunk = chunks_by_id.get(mapping["chunk_id"])
            if not chunk:
                continue
            preview = (chunk.text or "")[:PREVIEW_LENGTH]
            results.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "score": float(distances[0][rank]),
                    "text_preview": preview,
                    "metadata": chunk.metadata_json,
                }
            )

        if document_id is not None:
            filtered = [item for item in results if item["document_id"] == document_id]
            return filtered[:top_k]

        if len(results) <= 1:
            return results

        # Diversify across documents: keep early hits, but avoid single-doc dominance.
        per_doc_cap = max(1, min(2, top_k))
        by_doc: Dict[int, List[Dict[str, Any]]] = {}
        for item in results:
            by_doc.setdefault(item["document_id"], []).append(item)

        diversified: List[Dict[str, Any]] = []
        # First pass: take one from each document in rank order.
        seen_docs: set[int] = set()
        for item in results:
            doc_id = item["document_id"]
            if doc_id in seen_docs:
                continue
            diversified.append(item)
            seen_docs.add(doc_id)
            if len(diversified) >= top_k:
                return diversified

        # Second pass: fill remaining slots respecting per-doc cap.
        doc_counts = {item["document_id"]: 1 for item in diversified}
        for item in results:
            doc_id = item["document_id"]
            if doc_counts.get(doc_id, 0) >= per_doc_cap:
                continue
            if item in diversified:
                continue
            diversified.append(item)
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
            if len(diversified) >= top_k:
                break

        return diversified
