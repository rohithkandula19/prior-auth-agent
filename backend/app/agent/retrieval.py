"""Per-criterion evidence retrieval.

When a patient has many evidence items, feeding all of them to every
criterion check wastes tokens and dilutes the model's attention. This
module scores each evidence item against a criterion's text via TF-IDF
cosine similarity and returns the top-k most relevant. Sklearn is
already in requirements; no embedding API key needed.

Activates only when evidence count exceeds RETRIEVAL_THRESHOLD (default
20). Below that, the pipeline keeps passing every evidence item.
"""

from __future__ import annotations

import os
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.logging import get_logger
from app.schemas.patient import ClinicalEvidence

log = get_logger(__name__)

RETRIEVAL_THRESHOLD = int(os.environ.get("RETRIEVAL_THRESHOLD", "20"))
RETRIEVAL_TOPK = int(os.environ.get("RETRIEVAL_TOPK", "12"))


@lru_cache(maxsize=64)
def _vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_df=1.0,
        stop_words="english",
        lowercase=True,
    )


def select_relevant(
    criterion_text: str,
    evidence: list[ClinicalEvidence],
    *,
    top_k: int | None = None,
    threshold: int | None = None,
) -> list[ClinicalEvidence]:
    """Return top-k evidence items by TF-IDF similarity to the criterion.

    Below `threshold` items, returns the input unchanged.
    """
    n = len(evidence)
    th = threshold if threshold is not None else RETRIEVAL_THRESHOLD
    k = top_k or RETRIEVAL_TOPK
    if n <= th or n <= k:
        return list(evidence)

    docs = [criterion_text] + [
        f"{e.type} {e.description} {e.source_text}" for e in evidence
    ]
    try:
        vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", lowercase=True)
        matrix = vec.fit_transform(docs)
    except ValueError:
        # Empty vocabulary or similar; fall back to no filtering.
        return list(evidence)

    sims = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    # Take top-k indices, preserving original order for stability.
    top_idx = sorted(range(n), key=lambda i: sims[i], reverse=True)[:k]
    top_idx_sorted = sorted(top_idx)
    selected = [evidence[i] for i in top_idx_sorted]
    log.debug(
        "retrieval",
        candidates=n,
        kept=len(selected),
        top_score=round(float(sims.max()), 3),
    )
    return selected
