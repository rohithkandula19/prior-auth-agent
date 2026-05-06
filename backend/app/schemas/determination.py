from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

CriterionStatus = Literal["met", "not_met", "partial", "insufficient_evidence"]
DecisionType = Literal["approved", "denied", "needs_more_info"]


class CriterionEvaluation(BaseModel):
    criterion_id: str
    status: CriterionStatus
    supporting_evidence: list[str] = Field(
        default_factory=list, description="ClinicalEvidence ids that support the call"
    )
    policy_citation: tuple[int, int] = Field(..., description="char span in policy raw_text")
    chart_citations: list[tuple[int, int]] = Field(
        default_factory=list, description="char spans in patient raw_chart"
    )
    reasoning: str


class Determination(BaseModel):
    id: str
    patient_id: str
    policy_id: str
    decision: DecisionType
    confidence: float = Field(..., ge=0.0, le=1.0)
    criterion_evaluations: list[CriterionEvaluation]
    gaps: list[str] = Field(default_factory=list)
    recommended_action: str
    latency_ms: int
    cost_usd: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
