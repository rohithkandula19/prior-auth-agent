"""Offline demonstration of the criteria extraction pipeline.

Stubs out the Claude API call with a hand-authored JSON response that mirrors
what the real extractor would emit on the synthetic UHC MRI Lumbar policy.
The point is to exercise everything except the network: parse_text, span
re-derivation, Pydantic validation, FAISS index step (skipped here), and
final Policy assembly.

When you have an ANTHROPIC_API_KEY and a real PDF, replace this with:

    python -m app.ingestion.policy_indexer --policy data/policies/uhc_mri_lumbar.pdf ...
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.llm import ClaudeClient, LLMResponse  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.ingestion.criteria_extractor import CriteriaExtractor  # noqa: E402
from app.ingestion.policy_indexer import build_policy  # noqa: E402
from app.ingestion.policy_parser import parse_text  # noqa: E402

STUB_JSON = """[
  {"id": "C001", "text": "The member has had a documented neurologic examination performed by the\\n   ordering physician within the prior 30 days.", "type": "required", "parent_id": null, "page_number": 1},
  {"id": "C002", "text": "The member has completed at least six (6) weeks of physician-directed\\n   conservative therapy, including any combination of physical therapy,\\n   chiropractic care, anti-inflammatory medication, or activity modification,\\n   without clinically meaningful improvement.", "type": "required", "parent_id": null, "page_number": 1},
  {"id": "C002a", "text": "Progressive neurologic deficit (motor weakness, sensory loss, or reflex\\n      change) that has worsened over the most recent two-week period.", "type": "required", "parent_id": "C002", "page_number": 1},
  {"id": "C002b", "text": "Suspected cauda equina syndrome, including new-onset bowel or bladder\\n      dysfunction or saddle anesthesia.", "type": "required", "parent_id": "C002", "page_number": 1},
  {"id": "C002c", "text": "Known or suspected spinal infection, malignancy, or vertebral fracture\\n      based on imaging or clinical findings.", "type": "required", "parent_id": "C002", "page_number": 1},
  {"id": "C003", "text": "Plain radiographs of the lumbar spine have been performed and reviewed,\\n   unless an exception under criterion 2 applies.", "type": "required", "parent_id": null, "page_number": 1},
  {"id": "C101", "text": "The member has a non-MRI-compatible cardiac pacemaker, implanted\\n   defibrillator, cochlear implant, or other ferromagnetic implant for which\\n   MRI is contraindicated by the device manufacturer.", "type": "contraindication", "parent_id": null, "page_number": 1},
  {"id": "C102", "text": "The request is for screening of asymptomatic members.", "type": "contraindication", "parent_id": null, "page_number": 1},
  {"id": "C103", "text": "The same study has been performed within the prior six (6) months and there\\n   has been no documented change in clinical status.", "type": "contraindication", "parent_id": null, "page_number": 1},
  {"id": "D001", "text": "Office notes documenting the neurologic examination and current symptoms,\\n   including duration and severity.", "type": "documentation", "parent_id": null, "page_number": 1},
  {"id": "D002", "text": "Records of conservative therapy, including dates of service, type of\\n    therapy, and clinical response.", "type": "documentation", "parent_id": null, "page_number": 1},
  {"id": "D003", "text": "Reports of any prior imaging of the lumbar spine performed within the\\n     past twelve (12) months.", "type": "documentation", "parent_id": null, "page_number": 1},
  {"id": "D004", "text": "The clinical question that the requested MRI is intended to answer.", "type": "documentation", "parent_id": null, "page_number": 1}
]"""


class StubClient(ClaudeClient):
    def __init__(self) -> None:  # bypass real init
        self.model = "stub"

    def complete(self, prompt: str, **_: object) -> LLMResponse:
        return LLMResponse(
            text=STUB_JSON,
            input_tokens=len(prompt) // 4,
            output_tokens=len(STUB_JSON) // 4,
            cost_usd=0.0,
            latency_ms=0,
        )


def main() -> int:
    configure_logging()
    src = ROOT / "data" / "policies" / "uhc_mri_lumbar_synthetic.txt"
    parsed = parse_text(src.read_text(encoding="utf-8"))

    extractor = CriteriaExtractor(client=StubClient())
    policy, meta = build_policy(
        parsed,
        policy_id="uhc_mri_lumbar_synthetic",
        payer="UnitedHealthcare",
        procedure_code="72148",
        procedure_name="MRI Lumbar Spine",
        effective_date=date(2025, 1, 1),
        source_url="synthetic",
        extractor=extractor,
        skip_embeddings=True,
    )

    out_path = ROOT / "data" / "policies" / "uhc_mri_lumbar_synthetic.policy.json"
    out_path.write_text(policy.model_dump_json(indent=2), encoding="utf-8")

    summary = {
        "policy_id": policy.id,
        "criterion_count": len(policy.criteria),
        "by_type": {
            "required": sum(1 for c in policy.criteria if c.type == "required"),
            "contraindication": sum(1 for c in policy.criteria if c.type == "contraindication"),
            "documentation": sum(1 for c in policy.criteria if c.type == "documentation"),
        },
        "with_parent": sum(1 for c in policy.criteria if c.parent_id),
        "spans_resolved": sum(1 for c in policy.criteria if c.char_span != (0, 0)),
        "warnings": meta["warnings"],
        "out_file": str(out_path.relative_to(ROOT)),
    }
    print(json.dumps(summary, indent=2))

    print("\nFirst three criteria (id, type, parent, page, char_span, text head):")
    for c in policy.criteria[:3]:
        head = c.text.replace("\n", " ").strip()
        head = head[:90] + ("..." if len(head) > 90 else "")
        print(f"  {c.id:6s} {c.type:16s} parent={c.parent_id!s:6s} p{c.page_number} {c.char_span} {head}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
