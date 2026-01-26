import hashlib
from typing import Iterable, Protocol

import httpx

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


class RealEmbedder:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        dim: int,
        timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.dim = dim
        self.timeout = timeout

    def embed_texts(self, texts: Iterable[str]) -> np.ndarray:
        items = list(texts)
        if not items:
            return np.zeros((0, self.dim), dtype=np.float32)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "input": items}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/embeddings", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        embeddings = [item.get("embedding") for item in data.get("data", [])]
        if len(embeddings) != len(items):
            raise ValueError("Embedding response size mismatch.")

        vectors = np.array(embeddings, dtype=np.float32)
        if vectors.shape[1] != self.dim:
            raise ValueError(
                f"Embedding dim mismatch: got {vectors.shape[1]}, expected {self.dim}."
            )
        return vectors
