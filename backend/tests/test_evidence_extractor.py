"""Stub-LLM tests for EvidenceExtractor.

We don't hit Anthropic in unit tests. A StubClient returns a fixed JSON list
and we verify span re-derivation, dedup against existing evidence, and
warning behaviour for non-verbatim source_text.
"""

from __future__ import annotations

from pathlib import Path

from app.core.llm import ClaudeClient, LLMResponse
from app.extraction.chart_parser import parse_bundle_file
from app.extraction.evidence_extractor import EvidenceExtractor

DATA = Path(__file__).resolve().parents[2] / "data" / "patients" / "sample_back_pain.json"


class StubClient(ClaudeClient):
    def __init__(self, payload: str) -> None:  # bypass real init
        self.model = "stub"
        self._payload = payload

    def complete(self, prompt: str, **_: object) -> LLMResponse:
        return LLMResponse(
            text=self._payload,
            input_tokens=1,
            output_tokens=1,
            cost_usd=0.0,
            latency_ms=0,
        )


def test_augment_adds_verbatim_evidence() -> None:
    patient = parse_bundle_file(DATA)
    # Pick a substring that is verbatim in the chart
    verbatim = "Physical therapy procedure (8 weeks completed)"
    payload = (
        '[{"type":"note","description":"Completed 8 weeks of PT",'
        f'"source_text":"{verbatim}","date":"2025-03-19"}}]'
    )
    extractor = EvidenceExtractor(client=StubClient(payload))
    augmented, meta = extractor.augment(patient)

    assert meta["added"] == 1
    assert meta["warnings"] == []
    new = augmented.evidence[-1]
    assert new.source_text == verbatim
    s, x = new.char_span
    assert augmented.raw_chart[s:x] == verbatim


def test_augment_warns_on_non_verbatim() -> None:
    patient = parse_bundle_file(DATA)
    payload = (
        '[{"type":"note","description":"Patient reports moderate pain",'
        '"source_text":"the patient described moderate pain in the lumbar region",'
        '"date":"2025-04-01"}]'
    )
    extractor = EvidenceExtractor(client=StubClient(payload))
    augmented, meta = extractor.augment(patient)

    assert meta["added"] == 0
    assert any("non-verbatim" in w for w in meta["warnings"])
    assert len(augmented.evidence) == len(patient.evidence)


def test_augment_dedups_existing_source_text() -> None:
    patient = parse_bundle_file(DATA)
    # Reuse exactly the diagnosis line that is already in evidence
    existing = patient.evidence[0].source_text
    payload = (
        f'[{{"type":"diagnosis","description":"dup","source_text":"{existing}","date":null}}]'
    )
    extractor = EvidenceExtractor(client=StubClient(payload))
    augmented, meta = extractor.augment(patient)
    assert meta["added"] == 0
    assert len(augmented.evidence) == len(patient.evidence)


def test_augment_skips_invalid_type() -> None:
    patient = parse_bundle_file(DATA)
    payload = '[{"type":"foo","description":"bad","source_text":"Low back pain","date":null}]'
    extractor = EvidenceExtractor(client=StubClient(payload))
    augmented, meta = extractor.augment(patient)
    assert meta["added"] == 0
    assert any("invalid type" in w for w in meta["warnings"])
