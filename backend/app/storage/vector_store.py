"""Thin FAISS wrapper for per-policy criterion retrieval."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class IndexedChunk:
    chunk_id: str
    text: str
    metadata: dict


class FAISSStore:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.chunks: list[IndexedChunk] = []

    def add(self, vectors: np.ndarray, chunks: list[IndexedChunk]) -> None:
        if vectors.shape[0] != len(chunks):
            raise ValueError("vector count must equal chunk count")
        if vectors.shape[1] != self.dim:
            raise ValueError(f"expected dim {self.dim}, got {vectors.shape[1]}")
        # IP on L2-normalised vectors approximates cosine similarity.
        normed = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12)
        self.index.add(normed.astype(np.float32))
        self.chunks.extend(chunks)

    def search(self, query: np.ndarray, k: int = 5) -> list[tuple[float, IndexedChunk]]:
        q = query.reshape(1, -1).astype(np.float32)
        q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)
        scores, idxs = self.index.search(q, k)
        out: list[tuple[float, IndexedChunk]] = []
        for score, idx in zip(scores[0], idxs[0], strict=True):
            if idx == -1:
                continue
            out.append((float(score), self.chunks[idx]))
        return out

    def save(self, dir_path: str | Path) -> None:
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(dir_path / "index.faiss"))
        with (dir_path / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(
                    json.dumps(
                        {"chunk_id": c.chunk_id, "text": c.text, "metadata": c.metadata}
                    )
                    + "\n"
                )
        log.info("faiss_saved", dir=str(dir_path), chunks=len(self.chunks))

    @classmethod
    def load(cls, dir_path: str | Path) -> "FAISSStore":
        dir_path = Path(dir_path)
        index = faiss.read_index(str(dir_path / "index.faiss"))
        store = cls(dim=index.d)
        store.index = index
        with (dir_path / "chunks.jsonl").open(encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                store.chunks.append(
                    IndexedChunk(chunk_id=d["chunk_id"], text=d["text"], metadata=d["metadata"])
                )
        log.info("faiss_loaded", dir=str(dir_path), chunks=len(store.chunks))
        return store
