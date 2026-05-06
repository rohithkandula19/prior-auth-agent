"""Run a determination and fetch results."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.graph import run_determination
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
