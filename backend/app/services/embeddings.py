import hashlib
from typing import Iterable, Protocol

import numpy as np


class Embedder(Protocol):
    dim: int

    def embed_texts(self, texts: Iterable[str]) -> np.ndarray:
        ...


class HashEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed_texts(self, texts: Iterable[str]) -> np.ndarray:
        vectors = [self._embed_one(text) for text in texts]
        if not vectors:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.vstack(vectors).astype(np.float32)

    def _embed_one(self, text: str) -> np.ndarray:
        data = text.encode("utf-8")
        out = bytearray()
        counter = 0
        while len(out) < self.dim:
            hasher = hashlib.sha256()
            hasher.update(counter.to_bytes(4, "little"))
            hasher.update(data)
            out.extend(hasher.digest())
            counter += 1
        arr = np.frombuffer(bytes(out[: self.dim]), dtype=np.uint8).astype(np.float32)
        return arr / 255.0