"""Generate an appeal letter for a denied determination."""

from __future__ import annotations

from pathlib import Path

from app.core.llm import ClaudeClient, get_client
from app.core.logging import get_logger
from app.schemas.determination import Determination
from app.schemas.patient import Patient
from app.schemas.policy import Policy

log = get_logger(__name__)
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "appeal_letter.txt"


def _criterion_block(determination: Determination, policy: Policy, patient: Patient) -> str:
    crit_by_id = {c.id: c for c in policy.criteria}
    ev_by_id = {e.id: e for e in patient.evidence}
    rows: list[str] = []
    for ev in determination.criterion_evaluations:
        crit = crit_by_id.get(ev.criterion_id)
        if not crit:
            continue
        cited = []
        for eid in ev.supporting_evidence:
            e = ev_by_id.get(eid)
            if e:
                cited.append(f'    - "{e.source_text.strip()}"')
        cited_block = "\n".join(cited) if cited else "    - (no supporting evidence in chart)"
        rows.append(
            f"- {crit.id} [{crit.type} | status: {ev.status}]\n"
            f"  policy: {crit.text.strip()}\n"
            f"  reasoning: {ev.reasoning or '(none)'}\n"
            f"  chart citations:\n{cited_block}"
        )
    return "\n".join(rows)


def generate_appeal(
    determination: Determination,
    policy: Policy,
    patient: Patient,
    *,
    client: ClaudeClient | None = None,
) -> dict:
    client = client or get_client()
    template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.format(
        policy_payer=policy.payer,
        policy_procedure_name=policy.procedure_name,
        policy_procedure_code=policy.procedure_code,
        determination_id=determination.id,
        decision=determination.decision,
        confidence=f"{determination.confidence:.2f}",
        criterion_block=_criterion_block(determination, policy, patient),
        gaps_block=("\n".join(f"- {g}" for g in determination.gaps) or "- (none)"),
    )
    resp = client.complete(prompt, max_tokens=1200, temperature=0.2)
    log.info(
        "appeal_generated",
        determination_id=determination.id,
        cost_usd=round(resp.cost_usd, 4),
        latency_ms=resp.latency_ms,
        chars=len(resp.text),
    )
    return {
        "letter": resp.text.strip(),
        "cost_usd": resp.cost_usd,
        "latency_ms": resp.latency_ms,
    }
