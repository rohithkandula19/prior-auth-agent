"""End-to-end agent graph test with a deterministic stub LLM.

The stub returns hand-built JSON keyed off whichever criterion text appears
in the prompt, so we can drive the full graph through a known scenario:
all required criteria met, no contraindications met, no insufficient
evidence, expected approved decision.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.agent.graph import run_determination
from app.core.llm import ClaudeClient, LLMResponse
from app.extraction.chart_parser import parse_bundle_file
from app.ingestion.criteria_extractor import CriteriaExtractor
from app.ingestion.policy_indexer import build_policy
from app.ingestion.policy_parser import parse_text

ROOT = Path(__file__).resolve().parents[2]
SYNTH_POLICY = ROOT / "data" / "policies" / "uhc_mri_lumbar_synthetic.txt"
SAMPLE_PATIENT = ROOT / "data" / "patients" / "sample_back_pain.json"


# Same JSON the offline demo uses, kept inline so the test does not depend
# on regenerating the policy file.
EXTRACTOR_JSON = """[
  {"id": "C001", "text": "The member has had a documented neurologic examination performed by the\\n   ordering physician within the prior 30 days.", "type": "required", "parent_id": null, "page_number": 1},
  {"id": "C002", "text": "The member has completed at least six (6) weeks of physician-directed\\n   conservative therapy, including any combination of physical therapy,\\n   chiropractic care, anti-inflammatory medication, or activity modification,\\n   without clinically meaningful improvement.", "type": "required", "parent_id": null, "page_number": 1},
  {"id": "C003", "text": "Plain radiographs of the lumbar spine have been performed and reviewed,\\n   unless an exception under criterion 2 applies.", "type": "required", "parent_id": null, "page_number": 1},
  {"id": "C101", "text": "The member has a non-MRI-compatible cardiac pacemaker, implanted\\n   defibrillator, cochlear implant, or other ferromagnetic implant for which\\n   MRI is contraindicated by the device manufacturer.", "type": "contraindication", "parent_id": null, "page_number": 1}
]"""


class ExtractorStub(ClaudeClient):
    def __init__(self) -> None:
        self.model = "stub"

    def complete(self, prompt: str, **_: object) -> LLMResponse:
        return LLMResponse(EXTRACTOR_JSON, 1, 1, 0.0, 0)


class CheckerStub(ClaudeClient):
    """Returns a fixed verdict per criterion based on substring match."""

    def __init__(self) -> None:
        self.model = "stub"

    def complete(self, prompt: str, **_: object) -> LLMResponse:
        if "neurologic examination" in prompt and "30 days" in prompt:
            payload = {
                "status": "met",
                "supporting_evidence_ids": ["E0005"],
                "reasoning": "Neuro exam documented within window.",
                "confidence": 0.9,
            }
        elif "six (6) weeks" in prompt or "conservative therapy" in prompt:
            payload = {
                "status": "met",
                "supporting_evidence_ids": ["E0002", "E0003", "E0004"],
                "reasoning": "PT for 8 weeks plus ibuprofen documented.",
                "confidence": 0.88,
            }
        elif "Plain radiographs" in prompt:
            payload = {
                "status": "met",
                "supporting_evidence_ids": ["E0006"],
                "reasoning": "Lumbar XR documented prior to MRI request.",
                "confidence": 0.85,
            }
        elif "cardiac pacemaker" in prompt or "ferromagnetic" in prompt:
            payload = {
                "status": "not_met",
                "supporting_evidence_ids": [],
                "reasoning": "No incompatible implant in the chart.",
                "confidence": 0.95,
            }
        else:
            # Gap analysis or unknown
            payload = []  # type: ignore[assignment]
        text = json.dumps(payload)
        return LLMResponse(text, 1, 1, 0.0, 0)


def _build_policy() -> "Policy":  # noqa: F821
    parsed = parse_text(SYNTH_POLICY.read_text(encoding="utf-8"))
    extractor = CriteriaExtractor(client=ExtractorStub())
    policy, _ = build_policy(
        parsed,
        policy_id="uhc_mri_lumbar_test",
        payer="UnitedHealthcare",
        procedure_code="72148",
        procedure_name="MRI Lumbar Spine",
        effective_date=date(2025, 1, 1),
        source_url="synthetic",
        extractor=extractor,
        skip_embeddings=True,
    )
    return policy


def test_end_to_end_approved() -> None:
    policy = _build_policy()
    patient = parse_bundle_file(SAMPLE_PATIENT)

    determination = run_determination(policy, patient, client=CheckerStub())

    assert determination.decision == "approved"
    assert determination.confidence > 0.7
    statuses = {e.criterion_id: e.status for e in determination.criterion_evaluations}
    assert statuses["C001"] == "met"
    assert statuses["C002"] == "met"
    assert statuses["C003"] == "met"
    assert statuses["C101"] == "not_met"  # contraindication absent
    assert determination.gaps == []
    # Each met criterion has at least one valid chart citation
    for ev in determination.criterion_evaluations:
        if ev.status == "met":
            assert len(ev.chart_citations) >= 1
            for s, x in ev.chart_citations:
                assert 0 <= s <= x <= len(patient.raw_chart)
        # Policy citation always points into raw_text
        ps, pe = ev.policy_citation
        assert 0 <= ps <= pe <= len(policy.raw_text)


def test_denied_when_contraindication_met() -> None:
    policy = _build_policy()
    patient = parse_bundle_file(SAMPLE_PATIENT)

    class ContraStub(CheckerStub):
        def complete(self, prompt: str, **kw: object) -> LLMResponse:
            if "cardiac pacemaker" in prompt:
                return LLMResponse(
                    json.dumps(
                        {
                            "status": "met",
                            "supporting_evidence_ids": [],
                            "reasoning": "Patient has implanted defibrillator.",
                            "confidence": 0.97,
                        }
                    ),
                    1,
                    1,
                    0.0,
                    0,
                )
            return super().complete(prompt, **kw)

    determination = run_determination(policy, patient, client=ContraStub())
    assert determination.decision == "denied"
