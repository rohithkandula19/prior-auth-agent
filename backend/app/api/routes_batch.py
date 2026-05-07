"""Bulk determination runs.

POST /batch with a list of (patient_id, policy_id) pairs and we run them
all in parallel (capped by EVAL_CASE_CONCURRENCY). Returns a CSV download
plus a JSON summary.
"""

from __future__ import annotations

import csv
import os
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.agent.graph import run_determination
from app.core.logging import get_logger
from app.storage.repo import determination_repo, patient_repo, policy_repo

log = get_logger(__name__)
router = APIRouter(prefix="/batch", tags=["batch"])

CASE_WORKERS = int(os.environ.get("EVAL_CASE_CONCURRENCY", "4"))


class BatchPair(BaseModel):
    patient_id: str
    policy_id: str


class BatchRequest(BaseModel):
    pairs: list[BatchPair]


class BatchRow(BaseModel):
    patient_id: str
    policy_id: str
    determination_id: str | None
    decision: str
    confidence: float
    latency_ms: int
    cost_usd: float
    error: str | None = None


def _process(pair: BatchPair) -> BatchRow:
    patient = patient_repo.get(pair.patient_id)
    policy = policy_repo.get(pair.policy_id)
    if not patient or not policy:
        return BatchRow(
            patient_id=pair.patient_id,
            policy_id=pair.policy_id,
            determination_id=None,
            decision="error",
            confidence=0.0,
            latency_ms=0,
            cost_usd=0.0,
            error="patient or policy not found",
        )
    try:
        det = run_determination(policy, patient)
        determination_repo.put(det.id, det)
        return BatchRow(
            patient_id=pair.patient_id,
            policy_id=pair.policy_id,
            determination_id=det.id,
            decision=det.decision,
            confidence=det.confidence,
            latency_ms=det.latency_ms,
            cost_usd=det.cost_usd,
        )
    except Exception as exc:
        log.error("batch_row_error", patient_id=pair.patient_id, policy_id=pair.policy_id, error=str(exc))
        return BatchRow(
            patient_id=pair.patient_id,
            policy_id=pair.policy_id,
            determination_id=None,
            decision="error",
            confidence=0.0,
            latency_ms=0,
            cost_usd=0.0,
            error=str(exc),
        )


@router.post("/run")
async def run_batch(req: BatchRequest) -> dict:
    if not req.pairs:
        raise HTTPException(400, "pairs is empty")
    rows: list[BatchRow]
    if CASE_WORKERS > 1 and len(req.pairs) > 1:
        with ThreadPoolExecutor(max_workers=CASE_WORKERS) as ex:
            rows = list(ex.map(_process, req.pairs))
    else:
        rows = [_process(p) for p in req.pairs]
    n = len(rows)
    n_err = sum(1 for r in rows if r.error)
    return {
        "total": n,
        "errors": n_err,
        "by_decision": {
            d: sum(1 for r in rows if r.decision == d)
            for d in {"approved", "denied", "needs_more_info", "error"}
        },
        "rows": [r.model_dump() for r in rows],
    }


@router.post("/csv")
async def run_batch_csv(req: BatchRequest) -> Response:
    """Same as /batch/run but returns a CSV file."""
    if not req.pairs:
        raise HTTPException(400, "pairs is empty")
    if CASE_WORKERS > 1 and len(req.pairs) > 1:
        with ThreadPoolExecutor(max_workers=CASE_WORKERS) as ex:
            rows = list(ex.map(_process, req.pairs))
    else:
        rows = [_process(p) for p in req.pairs]

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "patient_id",
            "policy_id",
            "determination_id",
            "decision",
            "confidence",
            "latency_ms",
            "cost_usd",
            "error",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.patient_id,
                r.policy_id,
                r.determination_id or "",
                r.decision,
                f"{r.confidence:.3f}",
                r.latency_ms,
                f"{r.cost_usd:.4f}",
                r.error or "",
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="batch_results.csv"'},
    )
