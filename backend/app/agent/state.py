from typing import NotRequired, TypedDict

from app.schemas.determination import CriterionEvaluation
from app.schemas.patient import Patient
from app.schemas.policy import Policy


class AgentState(TypedDict, total=False):
    policy: Policy
    patient: Patient
    criterion_evaluations: list[CriterionEvaluation]
    gaps: list[str]
    confidence: float
    decision: NotRequired[str]
    reasoning_trace: list[str]
    cost_usd: float
    latency_ms: int
    # Per-criterion confidence in [0, 1] keyed by criterion_id, populated by
    # the criteria checker for use by the calibrator.
    per_criterion_confidence: NotRequired[dict[str, float]]
