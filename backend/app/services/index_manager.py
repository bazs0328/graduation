import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import faiss
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

    def is_ready(self) -> bool:
        return self.index is not None

    def search(self, query: str, top_k: int, db: Session) -> List[Dict[str, Any]]:
        if self.index is None:
            return []

        if self.index.ntotal == 0:
            return []

        vectors = self.embedder.embed_texts([query])
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

        return results
