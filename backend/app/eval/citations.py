"""Citation precision and recall.

A citation in our schema is a (start, end) char span into either the
policy or the chart. The gold set may specify expected citations as a
mapping criterion_id -> list of substrings; we resolve them to spans by
substring match against the canonical text.

For each gold citation substring, the predicted span is considered to
COVER it if their character ranges overlap by at least IoU >= 0.5.

We compute:
- citation_precision: among the agent's chart spans, the fraction that
  cover at least one gold citation for the corresponding criterion.
- citation_recall: among gold citations, the fraction that are covered
  by at least one agent span for the corresponding criterion.
- citation_f1: harmonic mean of the two.

Cases without expected_chart_citations contribute None (excluded from
aggregates) so adding gold spans is a strict additive upgrade.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.determination import CriterionEvaluation


@dataclass
class CitationScore:
    precision: float | None
    recall: float | None
    f1: float | None


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def _resolve_gold_spans(text: str, substrings: list[str]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for s in substrings:
        s = s.strip()
        if not s:
            continue
        idx = text.find(s)
        if idx >= 0:
            out.append((idx, idx + len(s)))
    return out


def score(
    chart_text: str,
    evaluations: list[CriterionEvaluation],
    expected: dict[str, list[str]] | None,
    *,
    iou_threshold: float = 0.5,
) -> CitationScore:
    if not expected:
        return CitationScore(None, None, None)

    by_id = {ev.criterion_id: ev for ev in evaluations}

    tp_pred = 0  # predicted spans that cover a gold span
    total_pred = 0
    tp_gold = 0  # gold spans covered by some predicted span
    total_gold = 0

    for crit_id, substrings in expected.items():
        gold_spans = _resolve_gold_spans(chart_text, substrings)
        ev = by_id.get(crit_id)
        pred_spans = list(ev.chart_citations) if ev else []

        total_pred += len(pred_spans)
        total_gold += len(gold_spans)

        for p in pred_spans:
            if any(_iou(p, g) >= iou_threshold for g in gold_spans):
                tp_pred += 1
        for g in gold_spans:
            if any(_iou(p, g) >= iou_threshold for p in pred_spans):
                tp_gold += 1

    precision = tp_pred / total_pred if total_pred else None
    recall = tp_gold / total_gold if total_gold else None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = None
    return CitationScore(
        precision=None if precision is None else round(precision, 3),
        recall=None if recall is None else round(recall, 3),
        f1=None if f1 is None else round(f1, 3),
    )
