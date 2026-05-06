"""Sanity-check citations on each evaluation. No LLM call here.

The criteria checker already attaches policy_citation (from the criterion's
char_span) and chart_citations (from cited evidence ids). This node verifies
that every cited span actually maps to a substring of the source text and
trims any citation that does not.

Splitting this into its own node makes it easy to add stronger citation
verification later (e.g. an entailment check) without touching the checker.
"""

from __future__ import annotations

from app.agent.state import AgentState
from app.core.logging import get_logger
from app.schemas.determination import CriterionEvaluation

log = get_logger(__name__)


def make_node():
    def run(state: AgentState) -> AgentState:
        policy = state["policy"]
        patient = state["patient"]
        evals = state.get("criterion_evaluations", [])
        verified: list[CriterionEvaluation] = []
        invalid_count = 0

        for ev in evals:
            ps, pe = ev.policy_citation
            valid_policy = 0 <= ps <= pe <= len(policy.raw_text)
            chart_spans: list[tuple[int, int]] = []
            for cs, ce in ev.chart_citations:
                if 0 <= cs <= ce <= len(patient.raw_chart):
                    chart_spans.append((cs, ce))
                else:
                    invalid_count += 1
            if not valid_policy:
                invalid_count += 1
                ps, pe = (0, 0)
            verified.append(
                ev.model_copy(
                    update={"policy_citation": (ps, pe), "chart_citations": chart_spans}
                )
            )

        if invalid_count:
            log.warning("citations_invalid_dropped", count=invalid_count)
        return {"criterion_evaluations": verified}

    return run
