"""Streaming variant of run_determination that yields NDJSON events as
each criterion is evaluated. The synchronous run_determination is kept
unchanged for callers that want the final result in a single response.

Event shapes (one JSON object per line):
  {"event":"started","criteria_count":N}
  {"event":"criterion","i":I,"total":N,"criterion_id":...,"status":...,"confidence":...}
  {"event":"citations_verified","invalid_dropped":K}
  {"event":"gaps","gaps":[...]}
  {"event":"calibrated","decision":...,"confidence":...}
  {"event":"done","determination_id":...}
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from app.agent.nodes import citation_generator, confidence_calibrator, gap_identifier
from app.agent.nodes.criteria_checker import _evidence_block
from app.core.llm import ClaudeClient, get_client
from app.core.logging import get_logger
from app.schemas.determination import CriterionEvaluation, Determination
from app.schemas.patient import Patient
from app.schemas.policy import Policy

log = get_logger(__name__)

PROMPT_PATH = (
    Path(__file__).resolve().parent / "prompts" / "criteria_checker.txt"
)
VALID_STATUS = {"met", "not_met", "partial", "insufficient_evidence"}


def _line(event: dict) -> bytes:
    return (json.dumps(event, default=str) + "\n").encode("utf-8")


async def stream_determination(
    policy: Policy,
    patient: Patient,
    *,
    client: ClaudeClient | None = None,
) -> AsyncIterator[bytes]:
    client = client or get_client()
    template = PROMPT_PATH.read_text(encoding="utf-8")
    ev_block = _evidence_block(patient)
    valid_ev_ids = {e.id for e in patient.evidence}

    yield _line({"event": "started", "criteria_count": len(policy.criteria)})

    evals: list[CriterionEvaluation] = []
    per_conf: dict[str, float] = {}
    cost = 0.0
    latency = 0
    start = time.monotonic()

    for i, crit in enumerate(policy.criteria, start=1):
        prompt = template.format(
            criterion_text=crit.text,
            criterion_type=crit.type,
            evidence_block=ev_block,
        )
        resp = client.complete(prompt, max_tokens=1024, temperature=0.0)
        cost += resp.cost_usd
        latency += resp.latency_ms

        status = "insufficient_evidence"
        cited_ids: list[str] = []
        confidence = 0.5
        reasoning = ""
        try:
            payload = resp.parse_json()
            if payload.get("status") in VALID_STATUS:
                status = payload["status"]
            cited_ids = [
                eid for eid in (payload.get("supporting_evidence_ids") or []) if eid in valid_ev_ids
            ]
            confidence = float(payload.get("confidence", 0.5))
            reasoning = payload.get("reasoning") or ""
        except Exception as exc:
            log.warning("stream_criterion_parse_failed", criterion_id=crit.id, error=str(exc))

        chart_spans = [
            e.char_span for e in patient.evidence if e.id in cited_ids
        ]
        evals.append(
            CriterionEvaluation(
                criterion_id=crit.id,
                status=status,  # type: ignore[arg-type]
                supporting_evidence=cited_ids,
                policy_citation=crit.char_span,
                chart_citations=chart_spans,
                reasoning=reasoning,
            )
        )
        per_conf[crit.id] = confidence

        yield _line(
            {
                "event": "criterion",
                "i": i,
                "total": len(policy.criteria),
                "criterion_id": crit.id,
                "criterion_type": crit.type,
                "status": status,
                "confidence": round(confidence, 3),
            }
        )

    # Citation verification
    state = {
        "policy": policy,
        "patient": patient,
        "criterion_evaluations": evals,
        "per_criterion_confidence": per_conf,
        "cost_usd": cost,
        "latency_ms": latency,
    }
    cit_node = citation_generator.make_node()
    state.update(cit_node(state) or {})  # type: ignore[arg-type]
    yield _line({"event": "citations_verified"})

    # Gaps
    gap_node = gap_identifier.make_node(client=client)
    state.update(gap_node(state) or {})  # type: ignore[arg-type]
    yield _line({"event": "gaps", "gaps": state.get("gaps", [])})

    # Calibrator
    cal_node = confidence_calibrator.make_node()
    state.update(cal_node(state) or {})  # type: ignore[arg-type]
    decision = state.get("decision", "needs_more_info")
    confidence = float(state.get("confidence", 0.0))
    yield _line(
        {
            "event": "calibrated",
            "decision": decision,
            "confidence": round(confidence, 3),
        }
    )

    wall_ms = int((time.monotonic() - start) * 1000)
    determination = Determination(
        id=f"det_{uuid.uuid4().hex[:10]}",
        patient_id=patient.id,
        policy_id=policy.id,
        decision=decision,  # type: ignore[arg-type]
        confidence=confidence,
        criterion_evaluations=state.get("criterion_evaluations", []),
        gaps=state.get("gaps", []),
        recommended_action=_recommend(decision, state.get("gaps", [])),
        latency_ms=wall_ms,
        cost_usd=cost,
    )

    yield _line(
        {
            "event": "done",
            "determination_id": determination.id,
            "latency_ms": wall_ms,
            "cost_usd": cost,
        }
    )

    # Persist via the same repo the synchronous path uses.
    from app.storage.repo import determination_repo

    determination_repo.put(determination.id, determination)  # type: ignore[union-attr]


def _recommend(decision: str, gaps: list[str]) -> str:
    if decision == "approved":
        return "Approve and issue authorization."
    if decision == "denied":
        return "Issue denial with policy citations and appeal instructions."
    if gaps:
        return "Request the following from the ordering provider:\n- " + "\n- ".join(gaps)
    return "Request additional clinical documentation before proceeding."
