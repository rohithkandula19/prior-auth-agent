"""Aggregate eval metrics. The harness writes a JSON summary to
data/eval_results/latest.json which the API reads back.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean, quantiles
from typing import Any

from app.config import settings

LATEST = Path("./data/eval_results/latest.json")


def _bin(p: float) -> str:
    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0001]
    for i in range(len(edges) - 1):
        if edges[i] <= p < edges[i + 1]:
            return f"{edges[i]:.1f}-{edges[i + 1]:.1f}".replace("1.0001", "1.0")
    return "unknown"


def reliability_diagram(records: list[dict]) -> list[dict]:
    """Group predictions by confidence bin and report bin-level accuracy."""
    by_bin: dict[str, list[dict]] = {}
    for r in records:
        by_bin.setdefault(_bin(r["confidence"]), []).append(r)
    out: list[dict] = []
    for label, rows in sorted(by_bin.items()):
        accuracy = mean(1.0 if r["agree"] else 0.0 for r in rows) if rows else 0.0
        avg_conf = mean(r["confidence"] for r in rows) if rows else 0.0
        out.append(
            {
                "bin": label,
                "count": len(rows),
                "accuracy": round(accuracy, 3),
                "avg_confidence": round(avg_conf, 3),
            }
        )
    return out


def expected_calibration_error(records: list[dict]) -> float:
    if not records:
        return 0.0
    total = len(records)
    err = 0.0
    for row in reliability_diagram(records):
        weight = row["count"] / total
        err += weight * abs(row["accuracy"] - row["avg_confidence"])
    return round(err, 4)


def latency_percentiles(records: list[dict]) -> dict[str, float]:
    vals = sorted(r["latency_ms"] for r in records)
    if not vals:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    if len(vals) < 2:
        return {"p50": float(vals[0]), "p95": float(vals[0]), "p99": float(vals[0])}
    qs = quantiles(vals, n=100, method="inclusive")
    return {
        "p50": round(qs[49], 1),
        "p95": round(qs[94], 1),
        "p99": round(qs[98], 1),
    }


def summarise(records: list[dict]) -> dict[str, Any]:
    if not records:
        return {"n": 0, "agreement": 0.0, "by_decision": {}}
    n = len(records)
    agreement = mean(1.0 if r["agree"] else 0.0 for r in records)
    by_decision = Counter(r["gold_decision"] for r in records)
    correct_by_decision = Counter(r["gold_decision"] for r in records if r["agree"])
    decision_breakdown = {
        d: {
            "n": by_decision[d],
            "correct": correct_by_decision[d],
            "accuracy": round(correct_by_decision[d] / by_decision[d], 3),
        }
        for d in by_decision
    }
    fm_counts = Counter(fm for r in records for fm in r.get("failure_modes", []))
    fm_total = sum(fm_counts.values()) or 1
    failure_modes = {
        k: {"count": v, "pct": round(v / fm_total, 3)}
        for k, v in fm_counts.most_common()
    }
    return {
        "run_version": "v1",
        "n": n,
        "agreement": round(agreement, 3),
        "ece": expected_calibration_error(records),
        "reliability": reliability_diagram(records),
        "by_decision": decision_breakdown,
        "latency_ms": latency_percentiles(records),
        "avg_cost_usd": round(mean(r["cost_usd"] for r in records), 4),
        "failure_modes": failure_modes,
    }


def latest_summary() -> dict[str, Any]:
    path = settings.gold_set_path.parent.parent / "eval_results" / "latest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if LATEST.exists():
        return json.loads(LATEST.read_text(encoding="utf-8"))
    return {"n": 0, "agreement": 0.0}
