"""End-to-end ingestion: PDF -> ParsedPolicy -> Criteria -> FAISS index -> Policy.

Run as a CLI:

    python -m app.ingestion.policy_indexer \
        --policy data/policies/uhc_mri_lumbar.pdf \
        --payer UnitedHealthcare \
        --procedure-code 72148 \
        --procedure-name "MRI Lumbar Spine" \
        --effective-date 2025-01-01 \
        --source-url https://example.com/policy
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from app.config import settings
from app.core.embeddings import EmbeddingClient, get_embedding_client
from app.core.logging import configure_logging, get_logger
from app.ingestion.criteria_extractor import CriteriaExtractor
from app.ingestion.policy_parser import ParsedPolicy, parse_pdf, parse_text
from app.schemas.policy import Policy
from app.storage.vector_store import FAISSStore, IndexedChunk

log = get_logger(__name__)


def build_policy(
    parsed: ParsedPolicy,
    *,
    policy_id: str,
    payer: str,
    procedure_code: str,
    procedure_name: str,
    effective_date: date,
    source_url: str,
    extractor: CriteriaExtractor | None = None,
    embedder: EmbeddingClient | None = None,
    index_dir: Path | None = None,
    skip_embeddings: bool = False,
) -> tuple[Policy, dict]:
    extractor = extractor or CriteriaExtractor()
    criteria, meta = extractor.extract(parsed)

    embedding_index_path: str | None = None
    if criteria and not skip_embeddings:
        embedder = embedder or get_embedding_client()
        texts = [c.text for c in criteria]
        vectors = embedder.embed(texts, input_type="document")
        store = FAISSStore(dim=vectors.shape[1])
        store.add(
            vectors,
            [
                IndexedChunk(
                    chunk_id=c.id,
                    text=c.text,
                    metadata={
                        "type": c.type,
                        "parent_id": c.parent_id,
                        "page_number": c.page_number,
                        "char_span": list(c.char_span),
                    },
                )
                for c in criteria
            ],
        )
        index_dir = index_dir or (settings.faiss_index_dir / policy_id)
        store.save(index_dir)
        embedding_index_path = str(index_dir)

    policy = Policy(
        id=policy_id,
        payer=payer,
        procedure_code=procedure_code,
        procedure_name=procedure_name,
        effective_date=effective_date,
        source_url=source_url,
        raw_text=parsed.raw_text,
        criteria=criteria,
        embedding_index_path=embedding_index_path,
    )
    return policy, meta


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Ingest a policy PDF into a Policy + FAISS index.")
    parser.add_argument("--policy", required=True, help="Path to PDF or .txt for synthetic input")
    parser.add_argument("--policy-id")
    parser.add_argument("--payer", default="UnitedHealthcare")
    parser.add_argument("--procedure-code", default="72148")
    parser.add_argument("--procedure-name", default="MRI Lumbar Spine")
    parser.add_argument("--effective-date", default="2025-01-01")
    parser.add_argument("--source-url", default="")
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip FAISS index build (useful when no embedding API key)",
    )
    parser.add_argument(
        "--out",
        help="Optional path to dump the resulting Policy as JSON",
    )
    args = parser.parse_args(argv)

    src = Path(args.policy)
    if src.suffix.lower() == ".pdf":
        parsed = parse_pdf(src)
    else:
        parsed = parse_text(src.read_text(encoding="utf-8"))

    policy_id = args.policy_id or src.stem
    policy, meta = build_policy(
        parsed,
        policy_id=policy_id,
        payer=args.payer,
        procedure_code=args.procedure_code,
        procedure_name=args.procedure_name,
        effective_date=date.fromisoformat(args.effective_date),
        source_url=args.source_url,
        skip_embeddings=args.skip_embeddings,
    )

    if args.out:
        Path(args.out).write_text(policy.model_dump_json(indent=2), encoding="utf-8")

    summary = {
        "policy_id": policy.id,
        "criterion_count": len(policy.criteria),
        "embedding_index_path": policy.embedding_index_path,
        **meta,
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
