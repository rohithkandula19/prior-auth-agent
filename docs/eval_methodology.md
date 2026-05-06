# Eval methodology

## What we measure

For every gold case we run the full pipeline (criteria extraction +
chart parsing + agent graph) and record:

| Metric | Definition |
| --- | --- |
| Agreement | 1 if `predicted_decision == gold_decision` else 0 |
| Per-decision accuracy | Agreement bucketed by gold decision class |
| ECE | Expected Calibration Error over confidence bins of width 0.2 |
| Reliability bins | accuracy and avg confidence per bin, for plotting |
| Citation precision | future: fraction of cited spans entailed by the source |
| Citation recall | future: fraction of gold-required spans actually cited |
| Latency p50/p95/p99 | wall-clock seconds end-to-end per case |
| Cost per case | sum of input + output token cost (Anthropic) or 0 (OpenRouter) |
| Failure mode counts | per the seven-mode taxonomy below |

ECE is computed with bin width 0.2; bins are `[0.0, 0.2)`, `[0.2, 0.4)`,
`...`, `[0.8, 1.0]`. Each bin contributes `weight * |accuracy - avg_conf|`
to the total error.

## Failure mode taxonomy

`backend/app/eval/failure_modes.py` classifies each case (a case can have
multiple modes). Definitions:

1. **hallucinated_criterion** -- the agent evaluated a criterion id that
   does not appear in the gold criteria for the case.
2. **missed_criterion** -- the gold criteria contain an id the agent did
   not evaluate.
3. **wrong_span_citation** -- a policy or chart citation has out-of-bounds
   offsets.
4. **evidence_misread** -- the agent cited an evidence id that does not
   exist on the patient.
5. **logical_error** -- decision disagrees with gold AND confidence is
   below 0.8 (the agent was uncertain and got it wrong; coachable).
6. **calibration_failure** -- decision disagrees with gold AND confidence
   is at least 0.8 (overconfident wrong answer; the most dangerous mode).
7. **latency_outlier** -- wall-clock latency over 30 seconds.

A pipeline error (exception during run) is recorded as `pipeline_error` so
infrastructure issues are not confused with model errors.

## Gold set construction

The bootstrap gold set at `data/gold_set/v1.jsonl` is intentionally tiny
(10 cases, all using the synthetic UHC policy) to wire up the harness and
let CI run cheaply. Real labels come next; the target is 100 case-policy
pairs stratified across approved / denied / needs_more_info, with 20
adversarial cases (contradictory evidence, ambiguous criteria, wrong
patient).

Each gold case has the shape:

```json
{
  "case_id": "uhc_mri_lumbar_001",
  "policy_path": "data/policies/uhc_mri_lumbar.pdf",
  "policy_id": "uhc_mri_lumbar",
  "patient_path": "data/patients/sample_back_pain.json",
  "expected_decision": "approved",
  "expected_criteria": {"C001": "met", "C002": "met"}
}
```

## Adversarial cases (planned)

Categories that should be in v1 of the gold set:

- **Contradictory evidence**: chart has both supporting and contradicting
  facts for the same criterion.
- **Ambiguous criteria**: policy uses words like "appropriate clinical
  context" that have no objective threshold.
- **Wrong patient**: chart actually belongs to a different procedure
  request; agent should produce `needs_more_info` rather than guessing.
- **Borderline durations**: 5 weeks 6 days of physical therapy when the
  threshold is 6 weeks.
- **Stale documentation**: prior imaging older than the policy's recency
  window.

These are designed to break specific failure modes from the taxonomy and
let us track regressions over time.

## How to run

```bash
# offline (stub LLM)
PYTHONPATH=backend .venv/bin/python scripts/run_eval.py --stub

# real LLM, full set
PYTHONPATH=backend .venv/bin/python scripts/run_eval.py

# subset
PYTHONPATH=backend .venv/bin/python scripts/run_eval.py --limit 5
```

Artifacts are written to `data/eval_results/`. The dashboard at `/eval`
reads `latest.json`.
