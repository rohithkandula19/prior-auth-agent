"""Aggregate per-criterion confidence into a single calibrated score and pick
a final decision.

v1: weighted aggregation with deterministic decision rules.
v2 (future): isotonic regression fit on the gold set, applied to v1 output.

Decision rules (in order):
- If any contraindication criterion has status == "met", decision = "denied".
- Top-level required criteria are checked. A top-level required criterion is
  considered "satisfied" if it is "met", OR if any of its children criteria
  (parent_id == top.id) is "met". This handles policy structures where the
  child clauses are exception alternatives that waive the parent's
  requirement.
- If all top-level required are satisfied, decision = "approved".
- If any top-level required is unsatisfied AND its status is "not_met"
  (chart actively contradicts) AND no child is "met", decision = "denied".
- Otherwise decision = "needs_more_info".
"""

from __future__ import annotations

from app.agent.state import AgentState
from app.core.logging import get_logger
from app.schemas.determination import CriterionEvaluation
from app.schemas.policy import Criterion

log = get_logger(__name__)


def _children_by_parent(criteria: list[Criterion]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in criteria:
        if c.parent_id:
            out.setdefault(c.parent_id, []).append(c.id)
    return out


def _decide(state: AgentState, evals: list[CriterionEvaluation]) -> str:
    by_id = {e.criterion_id: e for e in evals}
    policy = state["policy"]
    children = _children_by_parent(policy.criteria)

    contraind_ids = {c.id for c in policy.criteria if c.type == "contraindication"}
    if any(by_id.get(cid) and by_id[cid].status == "met" for cid in contraind_ids):
        return "denied"

    top_required = [
        c for c in policy.criteria if c.type == "required" and c.parent_id is None
    ]

    def child_met(crit_id: str) -> bool:
        for child in children.get(crit_id, []):
            ev = by_id.get(child)
            if ev and ev.status == "met":
                return True
        return False

    def is_satisfied(crit_id: str) -> bool:
        ev = by_id.get(crit_id)
        if ev and ev.status == "met":
            return True
        return child_met(crit_id)

    if not top_required:
        # Fall back to all required if there are no top-level ones at all.
        return "needs_more_info"

    if all(is_satisfied(c.id) for c in top_required):
        return "approved"

    # A required criterion is hard-failed only if status is not_met and no
    # exception clause covers it.
    for c in top_required:
        ev = by_id.get(c.id)
        if ev and ev.status == "not_met" and not child_met(c.id):
            return "denied"

    return "needs_more_info"


def _aggregate_confidence(per_conf: dict[str, float], evals: list[CriterionEvaluation]) -> float:
    if not evals:
        return 0.0
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
