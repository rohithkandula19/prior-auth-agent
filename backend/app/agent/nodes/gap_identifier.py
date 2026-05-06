"""When any criterion is insufficient_evidence, ask Claude what is missing."""

from __future__ import annotations

from pathlib import Path

from app.agent.state import AgentState
from app.core.llm import ClaudeClient, get_client
from app.core.logging import get_logger

log = get_logger(__name__)
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "gap_analysis.txt"


def make_node(client: ClaudeClient | None = None):
    client = client or get_client()
    template = PROMPT_PATH.read_text(encoding="utf-8")

    def run(state: AgentState) -> AgentState:
        policy = state["policy"]
        evals = state.get("criterion_evaluations", [])
        insufficient = [e for e in evals if e.status == "insufficient_evidence"]
        if not insufficient:
            return {"gaps": []}

        criteria_by_id = {c.id: c for c in policy.criteria}
        block = "\n".join(
            f"- {e.criterion_id}: {criteria_by_id[e.criterion_id].text}"
            for e in insufficient
            if e.criterion_id in criteria_by_id
        )
        resp = client.complete(template.format(insufficient_block=block), max_tokens=1024)
        try:
            gaps = resp.parse_json()
            if not isinstance(gaps, list):
                gaps = []
            gaps = [str(g) for g in gaps]
        except Exception as exc:
            log.warning("gap_parse_failed", error=str(exc))
            gaps = [f"Need additional documentation for criterion {e.criterion_id}" for e in insufficient]

        return {
            "gaps": gaps,
            "cost_usd": state.get("cost_usd", 0.0) + resp.cost_usd,
            "latency_ms": state.get("latency_ms", 0) + resp.latency_ms,
        }

    return run
