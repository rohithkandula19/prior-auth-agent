from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

EvidenceType = Literal["diagnosis", "medication", "procedure", "lab", "imaging", "note"]


class ClinicalEvidence(BaseModel):
    id: str
    type: EvidenceType
    code: str | None = Field(None, description="ICD-10, RxNorm, LOINC, or CPT code")
    description: str
    date: date
    source_text: str = Field(..., description="Verbatim chart excerpt")
    char_span: tuple[int, int]


class Patient(BaseModel):
    id: str
    age: int = Field(..., ge=0, le=130)
    sex: str
    evidence: list[ClinicalEvidence]
    raw_chart: str
