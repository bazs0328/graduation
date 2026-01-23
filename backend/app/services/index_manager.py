import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import faiss
from sqlalchemy.orm import Session

from app.db.models import Chunk
from app.services.embeddings import Embedder

logger = logging.getLogger("uvicorn.error")


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
