"""For each criterion, ask Claude whether it is met for this patient.

Criteria are independent, so we parallelise their LLM calls inside a
ThreadPoolExecutor. Default parallelism is 8, tuneable via the
EVAL_PARALLELISM environment variable (also used by run_determination).
The streaming variant (app.agent.streaming) keeps a sequential loop so
the UI can show per-criterion progress as it arrives.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.agent.state import AgentState
from app.core.llm import ClaudeClient, get_client
from app.core.logging import get_logger
from app.schemas.determination import CriterionEvaluation, CriterionStatus
from app.schemas.patient import Patient
from app.schemas.policy import Criterion

log = get_logger(__name__)
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "criteria_checker.txt"
VALID_STATUS: set[str] = {"met", "not_met", "partial", "insufficient_evidence"}

DEFAULT_PARALLELISM = int(os.environ.get("EVAL_PARALLELISM", "12"))


def _evidence_block(patient: Patient) -> str:
    return "\n".join(
        f"- {e.id} | {e.type} | {e.description} | date={e.date.isoformat()}"
        for e in patient.evidence
    )


def _evaluate_one(
    crit: Criterion,
    client: ClaudeClient,
    template: str,
    ev_block: str,
    valid_ev_ids: set[str],
    patient: Patient,
) -> tuple[CriterionEvaluation | None, float, int, float]:
    """Returns (evaluation_or_none, cost_usd, latency_ms, confidence)."""
    prompt = template.format(
        criterion_text=crit.text,
        criterion_type=crit.type,
        evidence_block=ev_block,
    )
    resp = client.complete(prompt, max_tokens=1024, temperature=0.0)
    try:
        payload = resp.parse_json()
    except Exception as exc:
        log.warning(
            "criterion_parse_failed",
            criterion_id=crit.id,
            error=str(exc),
            text_head=resp.text[:200],
        )
        return None, resp.cost_usd, resp.latency_ms, 0.5

    status = payload.get("status")
    if status not in VALID_STATUS:
        log.warning("criterion_invalid_status", criterion_id=crit.id, status=status)
        return None, resp.cost_usd, resp.latency_ms, 0.5

    cited_ids = [
        eid for eid in (payload.get("supporting_evidence_ids") or []) if eid in valid_ev_ids
    ]
    ev = CriterionEvaluation(
        criterion_id=crit.id,
        status=status,  # type: ignore[arg-type]
        supporting_evidence=cited_ids,
        policy_citation=crit.char_span,
        chart_citations=_chart_citations(patient, cited_ids),
        reasoning=payload.get("reasoning") or "",
    )
    try:
        confidence = float(payload.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    return ev, resp.cost_usd, resp.latency_ms, confidence


def make_node(client: ClaudeClient | None = None, *, parallelism: int | None = None):
    client = client or get_client()
    template = PROMPT_PATH.read_text(encoding="utf-8")
    workers = parallelism or DEFAULT_PARALLELISM

    def run(state: AgentState) -> AgentState:
        policy = state["policy"]
        patient = state["patient"]
        ev_block = _evidence_block(patient)
        valid_ev_ids = {e.id for e in patient.evidence}

        # Preserve criterion order in the output; the executor map respects it.
        results: list[tuple[CriterionEvaluation | None, float, int, float]]
        if workers > 1 and len(policy.criteria) > 1:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                results = list(
                    ex.map(
                        lambda c: _evaluate_one(
                            c, client, template, ev_block, valid_ev_ids, patient
                        ),
                        policy.criteria,
                    )
                )
        else:
            results = [
                _evaluate_one(c, client, template, ev_block, valid_ev_ids, patient)
                for c in policy.criteria
            ]

        evals: list[CriterionEvaluation] = []
        per_conf: dict[str, float] = {}
        cost = 0.0
        latency = 0
        for crit, (ev, c_cost, c_lat, c_conf) in zip(policy.criteria, results, strict=True):
            cost += c_cost
            latency += c_lat
            if ev is not None:
                evals.append(ev)
                per_conf[crit.id] = c_conf

        log.info(
            "criteria_checked",
            policy_id=policy.id,
            criteria=len(policy.criteria),
            evaluated=len(evals),
            workers=workers,
            cost_usd=round(cost, 4),
        )
        return {
            "criterion_evaluations": evals,
            "per_criterion_confidence": per_conf,
            "cost_usd": state.get("cost_usd", 0.0) + cost,
            "latency_ms": state.get("latency_ms", 0) + latency,
        }

    return run


def _chart_citations(patient: Patient, ev_ids: list[str]) -> list[tuple[int, int]]:
    by_id = {e.id: e for e in patient.evidence}
    return [by_id[i].char_span for i in ev_ids if i in by_id]


def criterion_status(eval_: CriterionEvaluation) -> CriterionStatus:
    return eval_.status
