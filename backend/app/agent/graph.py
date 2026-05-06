"""LangGraph supervisor wiring the four nodes plus the calibrator.

Topology:
    criteria_checker -> citation_generator -> gap_identifier -> calibrator -> END

We keep the graph linear because the four nodes are not independent:
- citation_generator runs after the checker because it verifies cite spans.
- gap_identifier reads the checker output to decide what is missing.
- calibrator reads everything to decide.

The "supervisor" name in the spec refers to the orchestrator, not a separate
node. LangGraph's StateGraph plays that role.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    citation_generator,
    confidence_calibrator,
    criteria_checker,
    gap_identifier,
)
from app.agent.state import AgentState
from app.core.llm import ClaudeClient
from app.schemas.determination import Determination
from app.schemas.patient import Patient
from app.schemas.policy import Policy


def build_graph(client: ClaudeClient | None = None) -> Any:
    g: StateGraph = StateGraph(AgentState)
    g.add_node("criteria_checker", criteria_checker.make_node(client=client))
    g.add_node("citation_generator", citation_generator.make_node())
    g.add_node("gap_identifier", gap_identifier.make_node(client=client))
    g.add_node("calibrator", confidence_calibrator.make_node())

    g.add_edge(START, "criteria_checker")
    g.add_edge("criteria_checker", "citation_generator")
    g.add_edge("citation_generator", "gap_identifier")
    g.add_edge("gap_identifier", "calibrator")
    g.add_edge("calibrator", END)
    return g.compile()


def run_determination(
    policy: Policy,
    patient: Patient,
    *,
    client: ClaudeClient | None = None,
    determination_id: str | None = None,
) -> Determination:
    graph = build_graph(client=client)
    initial: AgentState = {
        "policy": policy,
        "patient": patient,
        "cost_usd": 0.0,
        "latency_ms": 0,
        "reasoning_trace": [],
    }
    start = time.monotonic()
    result = graph.invoke(initial)
    wall_ms = int((time.monotonic() - start) * 1000)

    decision = result.get("decision", "needs_more_info")
    gaps = result.get("gaps", [])
    recommended = _recommend(decision, gaps)

    return Determination(
        id=determination_id or f"det_{uuid.uuid4().hex[:10]}",
        patient_id=patient.id,
        policy_id=policy.id,
        decision=decision,  # type: ignore[arg-type]
        confidence=float(result.get("confidence", 0.0)),
        criterion_evaluations=result.get("criterion_evaluations", []),
        gaps=gaps,
        recommended_action=recommended,
        latency_ms=wall_ms,
        cost_usd=float(result.get("cost_usd", 0.0)),
    )


def _recommend(decision: str, gaps: list[str]) -> str:
    if decision == "approved":
        return "Approve and issue authorization."
    if decision == "denied":
        return "Issue denial with policy citations and appeal instructions."
    if gaps:
        return "Request the following from the ordering provider:\n- " + "\n- ".join(gaps)
    return "Request additional clinical documentation before proceeding."
