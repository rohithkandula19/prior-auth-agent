"""Run a determination and fetch results."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.agent.appeal import generate_appeal
from app.agent.counterfactual import Counterfactual, generate_counterfactuals
from app.api.pdf_export import render_pdf
from app.agent.graph import run_determination
from app.agent.streaming import stream_determination
from app.schemas.determination import Determination
from app.storage.repo import determination_repo, patient_repo, policy_repo

router = APIRouter(tags=["determinations"])


class DetermineRequest(BaseModel):
    patient_id: str
    policy_id: str


@router.post("/determine", response_model=Determination)
async def determine(req: DetermineRequest) -> Determination:
    patient = patient_repo.get(req.patient_id)
    if not patient:
        raise HTTPException(404, "patient not found")
    policy = policy_repo.get(req.policy_id)
    if not policy:
        raise HTTPException(404, "policy not found")
    determination = run_determination(policy, patient)
    determination_repo.put(determination.id, determination)
    return determination


@router.get("/determinations/{determination_id}", response_model=Determination)
async def get_determination(determination_id: str) -> Determination:
    d = determination_repo.get(determination_id)
    if not d:
        raise HTTPException(404, "determination not found")
    return d


@router.get("/determinations", response_model=list[Determination])
async def list_determinations() -> list[Determination]:
    return determination_repo.list()


@router.post("/determinations/{determination_id}/appeal")
async def post_appeal(determination_id: str) -> dict:
    determination = determination_repo.get(determination_id)
    if not determination:
        raise HTTPException(404, "determination not found")
    policy = policy_repo.get(determination.policy_id)
    patient = patient_repo.get(determination.patient_id)
    if not policy or not patient:
        raise HTTPException(404, "policy or patient missing")
    return generate_appeal(determination, policy, patient)


@router.post(
    "/determinations/{determination_id}/counterfactuals",
    response_model=list[Counterfactual],
)
async def post_counterfactuals(determination_id: str) -> list[Counterfactual]:
    determination = determination_repo.get(determination_id)
    if not determination:
        raise HTTPException(404, "determination not found")
    policy = policy_repo.get(determination.policy_id)
    if not policy:
        raise HTTPException(404, "policy missing")
    return generate_counterfactuals(determination, policy)


@router.get("/determinations/{determination_id}/pdf")
async def get_determination_pdf(determination_id: str) -> Response:
    determination = determination_repo.get(determination_id)
    if not determination:
        raise HTTPException(404, "determination not found")
    policy = policy_repo.get(determination.policy_id)
    patient = patient_repo.get(determination.patient_id)
    if not policy or not patient:
        raise HTTPException(404, "policy or patient missing")
    pdf_bytes = render_pdf(determination, policy, patient)
    short = determination.id.upper().replace("DET_", "DET-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{short}.pdf"',
        },
    )


@router.post("/determine/stream")
async def determine_stream(req: DetermineRequest):
    patient = patient_repo.get(req.patient_id)
    if not patient:
        raise HTTPException(404, "patient not found")
    policy = policy_repo.get(req.policy_id)
    if not policy:
        raise HTTPException(404, "policy not found")
    return StreamingResponse(
        stream_determination(policy, patient),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
