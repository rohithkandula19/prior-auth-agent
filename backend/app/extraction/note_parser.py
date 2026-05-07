"""Build an ad-hoc Patient from a free-text clinical note for pre-submission
checks. No FHIR, no persistence. We split on blank lines and treat each
non-empty paragraph as one ClinicalEvidence (type=note) so each line has a
stable char_span the agent can cite into.
"""

from __future__ import annotations

import uuid
from datetime import date

from app.schemas.patient import ClinicalEvidence, Patient


def parse_note(
    note: str,
    *,
    patient_id: str | None = None,
    age: int = 0,
    sex: str = "U",
) -> Patient:
    note = note.replace("\r\n", "\n").strip() + "\n"
    pid = patient_id or f"draft_{uuid.uuid4().hex[:8]}"

    evidence: list[ClinicalEvidence] = []
    cursor = 0
    for raw_chunk in note.split("\n\n"):
        chunk = raw_chunk.strip()
        if not chunk:
            cursor += 1  # blank line
            continue
        # Locate the chunk's actual offset to keep spans honest even if we
        # collapsed leading whitespace.
        idx = note.find(chunk, cursor)
        if idx < 0:
            idx = cursor
        end = idx + len(chunk)
        evidence.append(
            ClinicalEvidence(
                id=f"E{len(evidence) + 1:04d}",
                type="note",
                code=None,
                description=chunk[:120].replace("\n", " "),
                date=date.today(),
                source_text=chunk,
                char_span=(idx, end),
            )
        )
        cursor = end

    return Patient(
        id=pid,
        age=age,
        sex=sex,
        evidence=evidence,
        raw_chart=note,
    )
