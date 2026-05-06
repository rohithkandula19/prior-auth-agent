from app.eval.citations import score
from app.schemas.determination import CriterionEvaluation

CHART = (
    "Patient SYNTH-1042 | age 52 | sex F\n"
    "2025-01-10 | diagnosis [M54.5] | Low back pain\n"
    "2025-03-19 | procedure [91251008] | Physical therapy procedure (8 weeks completed)\n"
    "2025-04-01 | lab [11506-3] | Neurologic examination - normal motor and sensory\n"
)


def _ev(criterion_id: str, chart_spans: list[tuple[int, int]]) -> CriterionEvaluation:
    return CriterionEvaluation(
        criterion_id=criterion_id,
        status="met",
        supporting_evidence=[],
        policy_citation=(0, 0),
        chart_citations=chart_spans,
        reasoning="",
    )


def test_perfect_score() -> None:
    needle = "Physical therapy procedure (8 weeks completed)"
    start = CHART.find(needle)
    end = start + len(needle)
    evaluations = [_ev("C002", [(start, end)])]
    s = score(CHART, evaluations, {"C002": [needle]})
    assert s.precision == 1.0
    assert s.recall == 1.0
    assert s.f1 == 1.0


def test_missing_recall() -> None:
    needle1 = "Physical therapy procedure (8 weeks completed)"
    needle2 = "Neurologic examination - normal motor and sensory"
    start1 = CHART.find(needle1)
    end1 = start1 + len(needle1)
    evaluations = [_ev("C002", [(start1, end1)])]
    s = score(CHART, evaluations, {"C002": [needle1, needle2]})
    assert s.precision == 1.0
    assert s.recall == 0.5
    assert s.f1 is not None and 0.6 < s.f1 < 0.7


def test_no_expected_returns_none() -> None:
    s = score(CHART, [], None)
    assert s.precision is None
    assert s.recall is None
    assert s.f1 is None


def test_iou_below_threshold() -> None:
    # Chart span only barely overlaps the needle: precision should drop.
    needle = "Physical therapy procedure (8 weeks completed)"
    start = CHART.find(needle)
    # Predicted span only covers the first 5 chars: IoU below 0.5
    evaluations = [_ev("C002", [(start, start + 5)])]
    s = score(CHART, evaluations, {"C002": [needle]})
    assert s.precision == 0.0
    assert s.recall == 0.0
