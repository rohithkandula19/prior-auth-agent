"""Eval runner.

Gold set format (one JSON object per line in a .jsonl file):

  {
    "case_id": "uhc_mri_lumbar_001",
    "policy_path": "data/policies/uhc_mri_lumbar_synthetic.txt",
    "policy_id": "uhc_mri_lumbar_synthetic",
    "patient_path": "data/patients/sample_back_pain.json",
    "expected_decision": "approved",
    "expected_criteria": {"C001":"met", "C002":"met", ...}
  }

The harness re-ingests the policy and patient on each run so cases are
self-contained. For policies without an .ingestion-pdf, it accepts a .txt
that goes through parse_text. The criteria extractor itself is mockable via
a factory hook.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.agent.graph import run_determination
from app.config import settings
from app.core.llm import ClaudeClient
from app.core.logging import get_logger
from app.eval.citations import score as score_citations
from app.eval.failure_modes import classify
from app.eval.metrics import summarise
from app.extraction.chart_parser import parse_bundle_file
from app.ingestion.criteria_extractor import CriteriaExtractor
from app.ingestion.policy_indexer import build_policy
from app.ingestion.policy_parser import parse_pdf, parse_text
from app.schemas.policy import Policy

log = get_logger(__name__)
ROOT = Path(__file__).resolve().parents[3]


class GoldCase(BaseModel):
    case_id: str
    policy_path: str
    policy_id: str
    patient_path: str
    expected_decision: str
    expected_criteria: dict[str, str] = Field(default_factory=dict)
    # Optional: per-criterion expected chart-citation substrings. Used to
    # compute citation precision/recall when present; cases without it
    # contribute None to the aggregate.
    expected_chart_citations: dict[str, list[str]] = Field(default_factory=dict)
    payer: str = "UnitedHealthcare"
    procedure_code: str = "72148"
    procedure_name: str = "MRI Lumbar Spine"
    effective_date: str = "2025-01-01"


class EvalRecord(BaseModel):
    case_id: str
    gold_decision: str
    predicted_decision: str
    confidence: float
    agree: bool
    cost_usd: float
    latency_ms: int
    failure_modes: list[str] = Field(default_factory=list)
    citation_precision: float | None = None
    citation_recall: float | None = None
    citation_f1: float | None = None


class EvalRun(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime
    n: int
    agreement: float
    summary: dict[str, Any]
    records: list[EvalRecord]


PolicyFactory = Callable[[GoldCase], Policy]
ClientFactory = Callable[[], ClaudeClient | None]


def _default_policy_factory(case: GoldCase) -> Policy:
    src = (ROOT / case.policy_path).resolve()
    if src.suffix.lower() == ".pdf":
        parsed = parse_pdf(src)
    else:
        parsed = parse_text(src.read_text(encoding="utf-8"))
    policy, _ = build_policy(
        parsed,
        policy_id=case.policy_id,
        payer=case.payer,
        procedure_code=case.procedure_code,
        procedure_name=case.procedure_name,
        effective_date=date.fromisoformat(case.effective_date),
        source_url="",
        extractor=CriteriaExtractor(),
        skip_embeddings=True,
    )
    return policy


def load_gold_set(path: str | Path | None = None) -> list[GoldCase]:
    p = Path(path) if path else settings.gold_set_path
    cases: list[GoldCase] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(GoldCase(**json.loads(line)))
    return cases


def run_eval(
    *,
    gold_set_path: str | Path | None = None,
    limit: int | None = None,
    policy_factory: PolicyFactory | None = None,
    client_factory: ClientFactory | None = None,
    out_dir: Path | None = None,
) -> EvalRun:
    cases = load_gold_set(gold_set_path)
    if limit:
        cases = cases[:limit]

    pf = policy_factory or _default_policy_factory
    cf = client_factory or (lambda: None)

    # Memoize policies across cases. The default extractor calls Claude
    # which is the single biggest cost; running it 10x for the same id is
    # pure waste. Cache key is policy_id since cases referencing the same
    # id should resolve to the same Policy object.
    policy_cache: dict[str, Policy] = {}

    def get_policy(case: GoldCase) -> Policy:
        if case.policy_id in policy_cache:
            return policy_cache[case.policy_id]
        p = pf(case)
        policy_cache[case.policy_id] = p
        return p

    started = datetime.utcnow()
    t0 = time.monotonic()
    records: list[EvalRecord] = []
    record_dicts: list[dict] = []

    for case in cases:
        try:
            policy = get_policy(case)
            patient = parse_bundle_file((ROOT / case.patient_path).resolve())
            determination = run_determination(policy, patient, client=cf())
        except Exception as exc:
            log.error("eval_case_error", case_id=case.case_id, error=str(exc))
            records.append(
                EvalRecord(
                    case_id=case.case_id,
                    gold_decision=case.expected_decision,
                    predicted_decision="error",
                    confidence=0.0,
                    agree=False,
                    cost_usd=0.0,
                    latency_ms=0,
                    failure_modes=["pipeline_error"],
                )
            )
            record_dicts.append(records[-1].model_dump())
            continue

        agree = determination.decision == case.expected_decision
        modes = classify(
            determination,
            gold_decision=case.expected_decision,
            gold_criteria_ids=set(case.expected_criteria.keys()) or {c.id for c in policy.criteria},
            valid_evidence_ids={e.id for e in patient.evidence},
            chart_len=len(patient.raw_chart),
            policy_len=len(policy.raw_text),
        )
        cit = score_citations(
            patient.raw_chart,
            determination.criterion_evaluations,
            case.expected_chart_citations or None,
        )
        rec = EvalRecord(
            case_id=case.case_id,
            gold_decision=case.expected_decision,
            predicted_decision=determination.decision,
            confidence=determination.confidence,
            agree=agree,
            cost_usd=determination.cost_usd,
            latency_ms=determination.latency_ms,
            failure_modes=modes,
            citation_precision=cit.precision,
            citation_recall=cit.recall,
            citation_f1=cit.f1,
        )
        records.append(rec)
        record_dicts.append(rec.model_dump())

    finished = datetime.utcnow()
    summary = summarise(record_dicts)
    run = EvalRun(
        run_id=f"eval_{uuid.uuid4().hex[:10]}",
        started_at=started,
        finished_at=finished,
        n=len(records),
        agreement=summary.get("agreement", 0.0),
        summary=summary,
        records=records,
    )

    out_dir = out_dir or (ROOT / "data" / "eval_results")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = run.model_dump(mode="json")
    (out_dir / f"{run.run_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out_dir / "latest.json").write_text(json.dumps(payload["summary"], indent=2), encoding="utf-8")
    log.info(
        "eval_run_complete",
        run_id=run.run_id,
        n=run.n,
        agreement=run.agreement,
        elapsed_s=round(time.monotonic() - t0, 2),
    )
    return run
