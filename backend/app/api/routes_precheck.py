"""Pre-submission check.

Provider pastes a draft note; we run the agent inline (no patient
persistence) and report which criteria are likely to clear, which are
not, and a concrete list of what to add to the note before submitting.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.graph import run_determination
from app.extraction.note_parser import parse_note
from app.schemas.determination import CriterionEvaluation, Determination
from app.storage.repo import determination_repo, patient_repo, policy_repo

router = APIRouter(prefix="/precheck", tags=["precheck"])


class PrecheckRequest(BaseModel):
    policy_id: str
    note: str = Field(..., min_length=10)
    age: int | None = None
    sex: str | None = None
    patient_id: str | None = None


class PrecheckRiskItem(BaseModel):
    criterion_id: str
    title: str
    why: str


class PrecheckResponse(BaseModel):
    determination: Determination
    likely_decision: str
    add_before_submitting: list[PrecheckRiskItem]
    will_clear: list[PrecheckRiskItem]
    confidence: float


def _short(text: str, n: int = 90) -> str:
    return " ".join(text.split())[:n]


@router.post("", response_model=PrecheckResponse)
async def post_precheck(req: PrecheckRequest) -> PrecheckResponse:
    policy = policy_repo.get(req.policy_id)
    if not policy:
        raise HTTPException(404, "policy not found")

    patient = parse_note(req.note, patient_id=req.patient_id, age=req.age or 0, sex=req.sex or "U")
    patient_repo.put(patient.id, patient)
    determination = run_determination(policy, patient)
    determination_repo.put(determination.id, determination)

    crit_by_id = {c.id: c for c in policy.criteria}

    add: list[PrecheckRiskItem] = []
    clear: list[PrecheckRiskItem] = []
    for ev in determination.criterion_evaluations:
        crit = crit_by_id.get(ev.criterion_id)
        if not crit:
            continue
        title = _short(crit.text)
        why = ev.reasoning or "No supporting evidence in note."
        item = PrecheckRiskItem(criterion_id=ev.criterion_id, title=title, why=why)
        if _is_blocking(ev, crit_by_id):
            add.append(item)
        elif ev.status == "met":
            clear.append(item)

    return PrecheckResponse(
        determination=determination,
        likely_decision=determination.decision,
        add_before_submitting=add,
        will_clear=clear,
        confidence=determination.confidence,
    )


def _is_blocking(ev: CriterionEvaluation, crit_by_id) -> bool:
    """A criterion blocks approval when it is not_met or insufficient AND
    no exception child clause covers it."""
    if ev.status == "met":
        return False
    crit = crit_by_id.get(ev.criterion_id)
    if not crit:
        return False
    if crit.type == "contraindication" and ev.status == "met":
        return True
    if crit.type == "contraindication":
        return False
    return ev.status in {"not_met", "insufficient_evidence", "partial"}
