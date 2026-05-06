"""Download a public payer policy PDF and ingest it through the agent.

Usage:
    python scripts/ingest_real_policy.py \
        --url https://www.uhcprovider.com/.../mri-lumbar-spine.pdf \
        --policy-id uhc_mri_lumbar \
        --payer UnitedHealthcare \
        --procedure-code 72148 \
        --procedure-name "MRI Lumbar Spine"

Or skip the download and point at a local file:

    python scripts/ingest_real_policy.py \
        --file ~/Downloads/UHC_MRI_Lumbar_2025.pdf \
        --policy-id uhc_mri_lumbar ...

The script:
  1. Downloads (or reads) the PDF.
  2. Calls the local backend's POST /policies/ingest (multipart) so the
     ingested policy is persisted in the same DB the UI reads from.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

DEFAULT_BACKEND = "http://localhost:8000"


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[fetch] {url}")
    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as r:
        r.raise_for_status()
        ctype = r.headers.get("content-type", "")
        if "pdf" not in ctype.lower() and not url.lower().endswith(".pdf"):
            raise SystemExit(f"URL does not look like a PDF (content-type: {ctype}). Refusing to save.")
        with dest.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    print(f"[saved] {dest} ({dest.stat().st_size} bytes)")
    return dest


def ingest(backend: str, pdf: Path, *, policy_id: str, payer: str, procedure_code: str,
           procedure_name: str, effective_date: str, source_url: str,
           skip_embeddings: bool) -> dict:
    print(f"[ingest] POST {backend}/policies/ingest")
    with pdf.open("rb") as f:
        files = {"file": (pdf.name, f, "application/pdf")}
        data = {
            "payer": payer,
            "procedure_code": procedure_code,
            "procedure_name": procedure_name,
            "effective_date": effective_date,
            "source_url": source_url,
            "policy_id": policy_id,
            "skip_embeddings": str(skip_embeddings).lower(),
        }
        r = httpx.post(f"{backend}/policies/ingest", files=files, data=data, timeout=600.0)
        r.raise_for_status()
        return r.json()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="Public PDF URL")
    src.add_argument("--file", help="Local PDF path")
    parser.add_argument("--save-to", default="data/policies",
                        help="Directory to save the downloaded file")
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--policy-id", required=True)
    parser.add_argument("--payer", required=True)
    parser.add_argument("--procedure-code", required=True)
    parser.add_argument("--procedure-name", required=True)
    parser.add_argument("--effective-date", default="2025-01-01")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--skip-embeddings", action="store_true", default=True)
    parser.add_argument("--with-embeddings", dest="skip_embeddings", action="store_false")
    args = parser.parse_args(argv)

    if args.url:
        filename = Path(args.url).name or f"{args.policy_id}.pdf"
        if not filename.lower().endswith(".pdf"):
            filename = f"{args.policy_id}.pdf"
        pdf = download(args.url, Path(args.save_to) / filename)
        if not args.source_url:
            args.source_url = args.url
    else:
        pdf = Path(args.file)
        if not pdf.exists():
            raise SystemExit(f"file not found: {pdf}")

    policy = ingest(
        args.backend,
        pdf,
        policy_id=args.policy_id,
        payer=args.payer,
        procedure_code=args.procedure_code,
        procedure_name=args.procedure_name,
        effective_date=args.effective_date,
        source_url=args.source_url,
        skip_embeddings=args.skip_embeddings,
    )
    print(f"[done] policy {policy['id']} | {len(policy.get('criteria', []))} criteria")
    print(f"  open http://localhost:3000/policies?selected={policy['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
