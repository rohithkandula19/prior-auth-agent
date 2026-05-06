"""Patient (chart) ingestion and retrieval."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.extraction.chart_parser import parse_bundle
from app.schemas.patient import Patient
from app.storage.repo import patient_repo

router = APIRouter(prefix="/patients", tags=["patients"])


class PatientIngest(BaseModel):
    fhir_bundle: dict[str, Any]
    patient_id: str | None = None


@router.post("", response_model=Patient)
async def create_patient(req: PatientIngest) -> Patient:
    try:
        patient = parse_bundle(req.fhir_bundle, patient_id=req.patient_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    pid = req.patient_id or patient.id or f"pt_{uuid.uuid4().hex[:8]}"
    if patient.id != pid:
        patient = patient.model_copy(update={"id": pid})
    patient_repo.put(pid, patient)
    return patient


@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str) -> Patient:
    p = patient_repo.get(patient_id)
    if not p:
        raise HTTPException(404, "patient not found")
    return p


@router.get("", response_model=list[Patient])
async def list_patients() -> list[Patient]:
    return patient_repo.list()


@router.post("/from_json")
async def ingest_raw_json(payload: str) -> Patient:
    """Convenience for clients that pass a serialized FHIR Bundle string."""
    try:
        bundle = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"invalid JSON: {exc}") from exc
    patient = parse_bundle(bundle)
    patient_repo.put(patient.id, patient)
    return patient
