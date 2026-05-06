"""CLI entrypoint for running the eval harness.

By default uses real Anthropic clients (so set ANTHROPIC_API_KEY). For a
fully offline smoke run, pass --stub which uses the same StubClient pair
the unit tests use, demonstrating the metrics pipeline end to end.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.logging import configure_logging  # noqa: E402
from app.eval.harness import GoldCase, run_eval  # noqa: E402


def _stub_factories():
    from datetime import date

    from app.core.llm import ClaudeClient, LLMResponse
    from app.ingestion.criteria_extractor import CriteriaExtractor
    from app.ingestion.policy_indexer import build_policy
    from app.ingestion.policy_parser import parse_text

    EXTRACTOR_JSON = (
        ROOT / "backend" / "tests" / "fixtures_extractor.json"
        if (ROOT / "backend" / "tests" / "fixtures_extractor.json").exists()
        else None
    )

    EXTRACTOR_PAYLOAD = """[
{"id":"C001","text":"The member has had a documented neurologic examination performed by the\\n   ordering physician within the prior 30 days.","type":"required","parent_id":null,"page_number":1},
{"id":"C002","text":"The member has completed at least six (6) weeks of physician-directed\\n   conservative therapy, including any combination of physical therapy,\\n   chiropractic care, anti-inflammatory medication, or activity modification,\\n   without clinically meaningful improvement.","type":"required","parent_id":null,"page_number":1},
{"id":"C003","text":"Plain radiographs of the lumbar spine have been performed and reviewed,\\n   unless an exception under criterion 2 applies.","type":"required","parent_id":null,"page_number":1},
{"id":"C101","text":"The member has a non-MRI-compatible cardiac pacemaker, implanted\\n   defibrillator, cochlear implant, or other ferromagnetic implant for which\\n   MRI is contraindicated by the device manufacturer.","type":"contraindication","parent_id":null,"page_number":1}
]"""

    class ExtractorStub(ClaudeClient):
        def __init__(self) -> None:
            self.model = "stub"

        def complete(self, prompt: str, **_):
            return LLMResponse(EXTRACTOR_PAYLOAD, 1, 1, 0.0, 0)

    class CheckerStub(ClaudeClient):
        def __init__(self) -> None:
            self.model = "stub"

        def complete(self, prompt: str, **_):
            if "neurologic examination" in prompt and "30 days" in prompt:
                payload = {"status": "met", "supporting_evidence_ids": ["E0005"], "reasoning": "Neuro exam documented.", "confidence": 0.9}
            elif "conservative therapy" in prompt or "six (6) weeks" in prompt:
                payload = {"status": "met", "supporting_evidence_ids": ["E0002", "E0003", "E0004"], "reasoning": "PT and ibuprofen.", "confidence": 0.88}
            elif "Plain radiographs" in prompt:
                payload = {"status": "met", "supporting_evidence_ids": ["E0006"], "reasoning": "Lumbar XR documented.", "confidence": 0.85}
            elif "ferromagnetic" in prompt or "cardiac pacemaker" in prompt:
                payload = {"status": "not_met", "supporting_evidence_ids": [], "reasoning": "No incompatible implant.", "confidence": 0.95}
            else:
                payload = []
            return LLMResponse(json.dumps(payload), 1, 1, 0.0, 0)

    def policy_factory(case: GoldCase):
        src = (ROOT / case.policy_path).resolve()
        parsed = parse_text(src.read_text(encoding="utf-8"))
        policy, _ = build_policy(
            parsed,
            policy_id=case.policy_id,
            payer=case.payer,
            procedure_code=case.procedure_code,
            procedure_name=case.procedure_name,
            effective_date=date.fromisoformat(case.effective_date),
            source_url="",
            extractor=CriteriaExtractor(client=ExtractorStub()),
            skip_embeddings=True,
        )
        return policy

    return policy_factory, lambda: CheckerStub()


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-set", default="data/gold_set/v1.jsonl")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--stub", action="store_true", help="Use stub LLM clients")
    args = parser.parse_args(argv)

    pf = cf = None
    if args.stub:
        pf, cf = _stub_factories()

    run = run_eval(
        gold_set_path=args.gold_set,
        limit=args.limit,
        policy_factory=pf,
        client_factory=cf,
    )
    print(json.dumps({"run_id": run.run_id, "summary": run.summary}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
