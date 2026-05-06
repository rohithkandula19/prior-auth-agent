"""Classify each eval-record disagreement into one or more failure modes."""

from __future__ import annotations

from app.schemas.determination import Determination

# Taxonomy from the architecture spec:
# 1. Hallucinated criterion - criterion checked that's not in policy
# 2. Missed criterion - criterion in policy not checked
# 3. Wrong span citation - citation doesn't support claim
# 4. Evidence misread - chart fact extracted incorrectly (out of band; needs gold spans)
# 5. Logical error - criteria met but decision denied or vice versa
# 6. Calibration failure - high confidence on wrong answer
# 7. Latency outlier - more than 30s

LATENCY_THRESHOLD_MS = 30_000


def classify(
    determination: Determination,
    *,
    gold_decision: str,
    gold_criteria_ids: set[str],
    valid_evidence_ids: set[str],
    chart_len: int,
    policy_len: int,
) -> list[str]:
    modes: list[str] = []
    checked = {e.criterion_id for e in determination.criterion_evaluations}

    if checked - gold_criteria_ids:
        modes.append("hallucinated_criterion")
    if gold_criteria_ids - checked:
        modes.append("missed_criterion")

    for ev in determination.criterion_evaluations:
        ps, pe = ev.policy_citation
        if not (0 <= ps <= pe <= policy_len):
            modes.append("wrong_span_citation")
            break
        bad = any(not (0 <= s <= x <= chart_len) for s, x in ev.chart_citations)
        if bad:
            modes.append("wrong_span_citation")
            break

    for ev in determination.criterion_evaluations:
        if any(eid not in valid_evidence_ids for eid in ev.supporting_evidence):
            modes.append("evidence_misread")
            break

    if determination.decision != gold_decision:
        # Distinguish a logical/decision flip from calibration failure
        if determination.confidence >= 0.8:
            modes.append("calibration_failure")
        else:
            modes.append("logical_error")

    if determination.latency_ms > LATENCY_THRESHOLD_MS:
        modes.append("latency_outlier")

    return modes
