"""Augment a Patient with narrative facts pulled from raw_chart via Claude.

Coded resources are handled by chart_parser. This step finds additional
narrative-only facts (durations, adherence, severity, failed therapies,
contraindications) that prior auth criteria typically need.

Each new evidence item must reference a verbatim chart substring; we
re-derive char_span from chart text rather than trusting model output.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.core.llm import ClaudeClient, get_client
from app.core.logging import get_logger
from app.schemas.patient import ClinicalEvidence, EvidenceType, Patient

log = get_logger(__name__)

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "agent" / "prompts" / "evidence_extraction.txt"
)
VALID_TYPES: set[EvidenceType] = {
    "diagnosis",
    "medication",
    "procedure",
    "lab",
    "imaging",
    "note",
}


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _locate(haystack: str, needle: str) -> tuple[int, int] | None:
    idx = haystack.find(needle)
    if idx < 0:
        return None
    return (idx, idx + len(needle))


def _parse_date(s: str | None, fallback: date) -> date:
    if not s:
        return fallback
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return fallback


class EvidenceExtractor:
    def __init__(self, client: ClaudeClient | None = None) -> None:
        self.client = client or get_client()
        self.prompt_template = _load_prompt()

    def augment(self, patient: Patient) -> tuple[Patient, dict]:
        prompt = self.prompt_template.format(chart_text=patient.raw_chart)
        resp = self.client.complete(prompt, max_tokens=4096, temperature=0.0)
        try:
            raw = resp.parse_json()
        except Exception as exc:
            log.error("evidence_json_parse_failed", error=str(exc), text_head=resp.text[:300])
            raise
        if not isinstance(raw, list):
            raise ValueError(f"Expected JSON array, got {type(raw).__name__}")

        existing_ids = {e.id for e in patient.evidence}
        existing_texts = {e.source_text for e in patient.evidence}
        next_idx = len(patient.evidence) + 1

        added: list[ClinicalEvidence] = []
        warnings: list[str] = []
        fallback_date = max((e.date for e in patient.evidence), default=date.today())

        for entry in raw:
            etype = entry.get("type")
            if etype not in VALID_TYPES:
                warnings.append(f"invalid type {etype!r}")
                continue
            source_text = (entry.get("source_text") or "").strip()
            if not source_text:
                continue
            if source_text in existing_texts:
                continue
            span = _locate(patient.raw_chart, source_text)
            if span is None:
                warnings.append(f"non-verbatim source_text: {source_text[:80]}")
                continue
            ev = ClinicalEvidence(
                id=f"E{next_idx:04d}",
                type=etype,
                code=None,
                description=(entry.get("description") or "").strip() or source_text[:120],
                date=_parse_date(entry.get("date"), fallback_date),
                source_text=source_text,
                char_span=span,
            )
            while ev.id in existing_ids:
                next_idx += 1
                ev = ev.model_copy(update={"id": f"E{next_idx:04d}"})
            existing_ids.add(ev.id)
            existing_texts.add(source_text)
            added.append(ev)
            next_idx += 1

        augmented = patient.model_copy(update={"evidence": [*patient.evidence, *added]})
        meta = {
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "cost_usd": resp.cost_usd,
            "latency_ms": resp.latency_ms,
            "added": len(added),
            "warnings": warnings,
        }
        log.info("evidence_augmented", patient_id=patient.id, **meta)
        return augmented, meta
