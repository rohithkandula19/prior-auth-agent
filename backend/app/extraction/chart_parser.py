"""Parse FHIR R4 Bundle JSON (e.g. Synthea output) into our Patient schema.

We intentionally do NOT pull a heavyweight FHIR library in. Synthea produces
predictable resource shapes, and we need only a handful of resource types:
Patient, Condition, MedicationRequest, Procedure, Observation, DiagnosticReport.

The parser produces:
- A list of ClinicalEvidence (one per resource), each carrying coded fields
  AND a flat source_text representation that we paste into raw_chart.
- A raw_chart string that concatenates each evidence's source_text with a
  stable header so char_span ranges line up with the final chart text.

Char spans are computed on the fly while building raw_chart so they always
match.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.schemas.patient import ClinicalEvidence, EvidenceType, Patient

log = get_logger(__name__)


def _coding(resource: dict[str, Any], field: str = "code") -> tuple[str | None, str]:
    """Pull (code, display) from a CodeableConcept-shaped field."""
    cc = resource.get(field) or {}
    codings = cc.get("coding") or []
    if codings:
        c = codings[0]
        return c.get("code"), c.get("display") or cc.get("text") or ""
    return None, cc.get("text") or ""


def _date(value: str | None) -> date:
    if not value:
        return date(1900, 1, 1)
    # FHIR date-time: 2024-03-15T08:00:00-05:00 or just 2024-03-15
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return date.fromisoformat(value[:10])
    except ValueError:
        return date(1900, 1, 1)


def _classify(resource: dict[str, Any]) -> EvidenceType | None:
    rt = resource.get("resourceType")
    if rt == "Condition":
        return "diagnosis"
    if rt == "MedicationRequest":
        return "medication"
    if rt == "Procedure":
        return "procedure"
    if rt == "Observation":
        category = ((resource.get("category") or [{}])[0].get("coding") or [{}])[0].get("code")
        if category == "imaging":
            return "imaging"
        if category in {"laboratory", "vital-signs"}:
            return "lab"
        return "lab"
    if rt == "DiagnosticReport":
        return "imaging"
    return None


def _resource_to_text(ev_type: EvidenceType, code: str | None, desc: str, dt: date,
                      resource: dict[str, Any]) -> str:
    """Render one resource as a single-line chart entry. Stable formatting matters
    because LLM citations will quote substrings of this output."""
    code_part = f" [{code}]" if code else ""
    extra = ""
    if ev_type == "lab":
        v = resource.get("valueQuantity") or {}
        if v:
            extra = f" value={v.get('value')} {v.get('unit') or ''}".rstrip()
    return f"{dt.isoformat()} | {ev_type}{code_part} | {desc}{extra}"


def _patient_demographics(resource: dict[str, Any]) -> tuple[int, str]:
    sex = (resource.get("gender") or "unknown")[0].upper()
    birth = resource.get("birthDate")
    age = 0
    if birth:
        b = _date(birth)
        today = date.today()
        age = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    return age, sex


def parse_bundle(bundle: dict[str, Any], patient_id: str | None = None) -> Patient:
    if bundle.get("resourceType") != "Bundle":
        raise ValueError("Expected FHIR Bundle resource")

    entries = bundle.get("entry") or []
    patient_resource: dict[str, Any] | None = None
    others: list[dict[str, Any]] = []
    for e in entries:
        r = e.get("resource") or {}
        if r.get("resourceType") == "Patient" and patient_resource is None:
            patient_resource = r
        else:
            others.append(r)

    if patient_resource is None:
        raise ValueError("Bundle has no Patient resource")

    age, sex = _patient_demographics(patient_resource)
    pid = patient_id or patient_resource.get("id") or "unknown"

    chart_lines: list[str] = []
    evidence: list[ClinicalEvidence] = []
    cursor = 0

    def _append(line: str) -> tuple[int, int]:
        nonlocal cursor
        start = cursor
        chart_lines.append(line)
        cursor += len(line) + 1  # newline
        return start, cursor - 1  # span excludes the newline

    # Header
    header = f"Patient {pid} | age {age} | sex {sex}"
    _append(header)

    for resource in others:
        ev_type = _classify(resource)
        if ev_type is None:
            continue
        # MedicationRequest puts the coded med under medicationCodeableConcept,
        # not under "code". Use that field for display + code.
        code_field = "medicationCodeableConcept" if ev_type == "medication" else "code"
        code, display = _coding(resource, code_field)
        if not display:
            display = resource.get("resourceType") or ""
        # Pick the most relevant date
        dt_str = (
            resource.get("onsetDateTime")
            or resource.get("authoredOn")
            or resource.get("performedDateTime")
            or resource.get("effectiveDateTime")
            or resource.get("issued")
            or resource.get("recordedDate")
        )
        dt = _date(dt_str)
        line = _resource_to_text(ev_type, code, display, dt, resource)
        span = _append(line)

        evidence.append(
            ClinicalEvidence(
                id=f"E{len(evidence) + 1:04d}",
                type=ev_type,
                code=code,
                description=display,
                date=dt,
                source_text=line,
                char_span=span,
            )
        )

    raw_chart = "\n".join(chart_lines)
    log.info("chart_parsed", patient_id=pid, evidence_count=len(evidence), chart_chars=len(raw_chart))

    return Patient(id=pid, age=age, sex=sex, evidence=evidence, raw_chart=raw_chart)


def parse_bundle_file(path: str | Path) -> Patient:
    path = Path(path)
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return parse_bundle(bundle, patient_id=path.stem)
