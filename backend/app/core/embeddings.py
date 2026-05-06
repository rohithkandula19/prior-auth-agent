"""Embedding client. Defaults to Voyage AI since Anthropic does not host embeddings."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import voyageai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class EmbeddingClient:
    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or settings.anthropic_embedding_model
        resolved_key = api_key or settings.voyage_api_key or None
        self._client = voyageai.Client(api_key=resolved_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def embed(self, texts: Sequence[str], input_type: str = "document") -> np.ndarray:
        if not texts:
            return np.zeros((0, 1024), dtype=np.float32)
        result = self._client.embed(list(texts), model=self.model, input_type=input_type)
        arr = np.asarray(result.embeddings, dtype=np.float32)
        log.debug("embed", count=len(texts), dim=arr.shape[1])
        return arr


def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()
