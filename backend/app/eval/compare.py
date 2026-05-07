"""Run the same gold set against multiple models and compare them.

This is the eval-harness deliverable that's hard to fake: same cases,
same gold labels, swap only the model. Reports per-model agreement,
citation P/R/F1, calibration error, latency, and total cost so you can
make a real cost-vs-quality call.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.llm import OpenRouterClient
from app.core.logging import get_logger
from app.eval.harness import EvalRun, run_eval

log = get_logger(__name__)


def run_compare(
    models: list[str],
    *,
    gold_set_path: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run the eval once per model in `models` and return a comparison."""
    if not models:
        raise ValueError("models list is empty")
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for A/B comparison")

    runs: dict[str, EvalRun] = {}
    for m in models:
        log.info("compare_run_starting", model=m)

        def factory(model_name: str = m):
            return OpenRouterClient(model=model_name)

        runs[m] = run_eval(
            gold_set_path=gold_set_path,
            limit=limit,
            client_factory=factory,
        )

    by_model = {
        m: {
            "n": run.n,
            "agreement": run.agreement,
            "ece": run.summary.get("ece"),
            "citations": run.summary.get("citations"),
            "latency_ms": run.summary.get("latency_ms"),
            "avg_cost_usd": run.summary.get("avg_cost_usd"),
            "by_decision": run.summary.get("by_decision"),
            "failure_modes": run.summary.get("failure_modes"),
        }
        for m, run in runs.items()
    }

    # Pick a baseline (first model) and compute deltas for the rest.
    baseline = models[0]
    deltas: dict[str, dict[str, float | None]] = {}
    base = by_model[baseline]
    for m in models[1:]:
        cur = by_model[m]
        deltas[m] = {
            "agreement_diff": _diff(cur["agreement"], base["agreement"]),
            "ece_diff": _diff(cur["ece"], base["ece"]),
            "p95_latency_diff_ms": _diff(
                _get(cur, "latency_ms", "p95"),
                _get(base, "latency_ms", "p95"),
            ),
            "cost_diff_usd": _diff(cur["avg_cost_usd"], base["avg_cost_usd"]),
        }

    return {
        "baseline": baseline,
        "models": models,
        "by_model": by_model,
        "deltas": deltas,
    }


def _diff(a, b) -> float | None:
    if a is None or b is None:
        return None
    try:
        return round(float(a) - float(b), 4)
    except (TypeError, ValueError):
        return None


def _get(d: dict, *path):
    cur = d
    for p in path:
        if cur is None:
            return None
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur
