"""Aggregate per-criterion confidence into a single calibrated score and pick
a final decision.

v1: weighted aggregation with deterministic decision rules.
v2 (future): isotonic regression fit on the gold set, applied to v1 output.

Decision rules (in order):
- If any contraindication criterion has status == "met", decision = "denied".
- If all required criteria have status == "met", decision = "approved".
- If any required criterion has status == "not_met", decision = "denied".
- Otherwise decision = "needs_more_info".
"""

from __future__ import annotations

from app.agent.state import AgentState
from app.core.logging import get_logger
from app.schemas.determination import CriterionEvaluation

log = get_logger(__name__)


def _required_criteria_ids(state: AgentState) -> set[str]:
    return {c.id for c in state["policy"].criteria if c.type == "required"}


def _contraindication_ids(state: AgentState) -> set[str]:
    return {c.id for c in state["policy"].criteria if c.type == "contraindication"}


def _decide(state: AgentState, evals: list[CriterionEvaluation]) -> str:
    required = _required_criteria_ids(state)
    contraind = _contraindication_ids(state)
    by_id = {e.criterion_id: e for e in evals}

    if any(by_id.get(cid) and by_id[cid].status == "met" for cid in contraind):
        return "denied"

    required_evals = [by_id[r] for r in required if r in by_id]
    if required_evals and all(e.status == "met" for e in required_evals):
        return "approved"
    if any(e.status == "not_met" for e in required_evals):
        return "denied"
    return "needs_more_info"


def _aggregate_confidence(per_conf: dict[str, float], evals: list[CriterionEvaluation]) -> float:
    if not evals:
        return 0.0
    # Weighted by criticality: a contraindication or "not_met" required carries
    # more weight in the aggregate because it likely drives the decision.
    weights: dict[str, float] = {}
    for e in evals:
        w = 1.0
        if e.status == "not_met":
            w = 2.0
        weights[e.criterion_id] = w

    num = sum(per_conf.get(eid, 0.5) * w for eid, w in weights.items())
    den = sum(weights.values()) or 1.0
    return max(0.0, min(1.0, num / den))


def make_node():
    def run(state: AgentState) -> AgentState:
        evals = state.get("criterion_evaluations", [])
        per_conf = state.get("per_criterion_confidence", {}) or {}
        decision = _decide(state, evals)
        confidence = _aggregate_confidence(per_conf, evals)

        # If there is any insufficient_evidence and decision is needs_more_info,
        # cap confidence so we do not overstate certainty about a non-decision.
        if decision == "needs_more_info":
            confidence = min(confidence, 0.6)

        log.info(
            "calibration",
            decision=decision,
            confidence=round(confidence, 3),
            criteria=len(evals),
        )
        return {"decision": decision, "confidence": confidence}

    return run
