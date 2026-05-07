"""Counterfactual analysis: 'what would flip this determination?'"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from app.core.llm import ClaudeClient, get_client
from app.core.logging import get_logger
from app.schemas.determination import Determination
from app.schemas.policy import Policy

log = get_logger(__name__)
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "counterfactual.txt"


class Counterfactual(BaseModel):
    target_criterion_id: str
    add_to_chart: str
    expected_status_after: str
    predicted_decision_after: str
    rationale: str


def _block(determination: Determination, policy: Policy) -> str:
    crit_by_id = {c.id: c for c in policy.criteria}
    rows: list[str] = []
    for ev in determination.criterion_evaluations:
        crit = crit_by_id.get(ev.criterion_id)
        if not crit:
            continue
        rows.append(
            f"- {crit.id} [{crit.type} | status: {ev.status}]\n"
            f"  policy: {crit.text.strip()}\n"
            f"  reasoning: {ev.reasoning or '(none)'}"
        )
    return "\n".join(rows)


def generate_counterfactuals(
    determination: Determination,
    policy: Policy,
    *,
    client: ClaudeClient | None = None,
) -> list[Counterfactual]:
    client = client or get_client()
    template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.format(
        decision=determination.decision,
        confidence=f"{determination.confidence:.2f}",
        criterion_block=_block(determination, policy),
        gaps_block=("\n".join(f"- {g}" for g in determination.gaps) or "- (none)"),
    )
    resp = client.complete(prompt, max_tokens=1500, temperature=0.1)
    try:
        raw = resp.parse_json()
    except Exception as exc:
        log.warning("counterfactual_parse_failed", error=str(exc), text_head=resp.text[:200])
        return []
    if not isinstance(raw, list):
        return []
    out: list[Counterfactual] = []
    for entry in raw[:4]:
        try:
            out.append(Counterfactual(**entry))
        except Exception as exc:
            log.warning("counterfactual_entry_invalid", entry=str(entry), error=str(exc))
    log.info(
        "counterfactuals_generated",
        determination_id=determination.id,
        count=len(out),
        cost_usd=round(resp.cost_usd, 4),
    )
    return out
