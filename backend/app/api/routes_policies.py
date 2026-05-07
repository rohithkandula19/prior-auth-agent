"""Policy ingestion and retrieval endpoints."""

from __future__ import annotations

import tempfile
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.ingestion.criteria_extractor import CriteriaExtractor
from app.ingestion.policy_indexer import build_policy
from app.ingestion.policy_parser import parse_pdf, parse_text
from app.schemas.policy import Criterion, Policy
from app.storage.db import PolicyVersionRow, SessionLocal
from app.storage.repo import policy_repo

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyTextIngest(BaseModel):
    text: str
    payer: str = "UnitedHealthcare"
    procedure_code: str = "72148"
    procedure_name: str = "MRI Lumbar Spine"
    effective_date: date = date(2025, 1, 1)
    source_url: str = ""
    policy_id: str | None = None
    skip_embeddings: bool = True


@router.post("/ingest", response_model=Policy)
async def ingest_pdf(
    file: UploadFile,
    payer: str = Form("UnitedHealthcare"),
    procedure_code: str = Form("72148"),
    procedure_name: str = Form("MRI Lumbar Spine"),
    effective_date: str = Form("2025-01-01"),
    source_url: str = Form(""),
    policy_id: str | None = Form(None),
    skip_embeddings: bool = Form(True),
) -> Policy:
    if not file.filename:
        raise HTTPException(400, "filename required")
    suffix = Path(file.filename).suffix.lower() or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        if suffix == ".pdf":
            parsed = parse_pdf(tmp_path)
        else:
            parsed = parse_text(tmp_path.read_text(encoding="utf-8"))
    finally:
        tmp_path.unlink(missing_ok=True)

    pid = policy_id or f"policy_{uuid.uuid4().hex[:8]}"
    policy, _ = build_policy(
        parsed,
        policy_id=pid,
        payer=payer,
        procedure_code=procedure_code,
        procedure_name=procedure_name,
        effective_date=date.fromisoformat(effective_date),
        source_url=source_url,
        extractor=CriteriaExtractor(),
        skip_embeddings=skip_embeddings,
    )
    policy_repo.put(pid, policy)
    return policy


@router.post("/ingest_text", response_model=Policy)
async def ingest_text(req: PolicyTextIngest) -> Policy:
    parsed = parse_text(req.text)
    pid = req.policy_id or f"policy_{uuid.uuid4().hex[:8]}"
    policy, _ = build_policy(
        parsed,
        policy_id=pid,
        payer=req.payer,
        procedure_code=req.procedure_code,
        procedure_name=req.procedure_name,
        effective_date=req.effective_date,
        source_url=req.source_url,
        extractor=CriteriaExtractor(),
        skip_embeddings=req.skip_embeddings,
    )
    policy_repo.put(pid, policy)
    return policy


@router.get("", response_model=list[Policy])
async def list_policies() -> list[Policy]:
    return policy_repo.list()


@router.get("/{policy_id}", response_model=Policy)
async def get_policy(policy_id: str) -> Policy:
    p = policy_repo.get(policy_id)
    if not p:
        raise HTTPException(404, "policy not found")
    return p


@router.get("/{policy_id}/criteria", response_model=list[Criterion])
async def get_criteria(policy_id: str) -> list[Criterion]:
    p = policy_repo.get(policy_id)
    if not p:
        raise HTTPException(404, "policy not found")
    return p.criteria


@router.get("/{policy_id}/versions")
async def list_versions(policy_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(PolicyVersionRow)
            .filter(PolicyVersionRow.policy_id == policy_id)
            .order_by(PolicyVersionRow.version.desc())
            .all()
        )
        return [
            {
                "version": r.version,
                "created_at": r.created_at.isoformat(),
                "criterion_count": len(r.data.get("criteria", [])),
                "effective_date": r.data.get("effective_date"),
            }
            for r in rows
        ]


@router.get("/{policy_id}/diff")
async def diff_versions(policy_id: str, a: int, b: int) -> dict:
    with SessionLocal() as session:
        rows = {
            r.version: r
            for r in session.query(PolicyVersionRow)
            .filter(PolicyVersionRow.policy_id == policy_id)
            .filter(PolicyVersionRow.version.in_([a, b]))
            .all()
        }
    if a not in rows or b not in rows:
        raise HTTPException(404, "version not found")
    crit_a = {c["id"]: c["text"] for c in rows[a].data.get("criteria", [])}
    crit_b = {c["id"]: c["text"] for c in rows[b].data.get("criteria", [])}
    added = sorted(set(crit_b.keys()) - set(crit_a.keys()))
    removed = sorted(set(crit_a.keys()) - set(crit_b.keys()))
    changed = [
        cid for cid in (crit_a.keys() & crit_b.keys()) if crit_a[cid] != crit_b[cid]
    ]
    return {
        "policy_id": policy_id,
        "a": a,
        "b": b,
        "added": added,
        "removed": removed,
        "changed": sorted(changed),
        "added_text": {cid: crit_b[cid] for cid in added},
        "removed_text": {cid: crit_a[cid] for cid in removed},
        "changed_text": {cid: {"a": crit_a[cid], "b": crit_b[cid]} for cid in changed},
    }
