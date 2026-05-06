# Failure modes

A short reference for the seven categories the eval harness emits, with
what to look for and what tends to fix each one.

## 1. hallucinated_criterion

The agent evaluated a criterion that the policy does not contain.

- **Where it lives**: criteria extraction. The model invented a structure
  the source did not authorize.
- **Detector**: `set(predicted_ids) - set(gold_ids)`.
- **Likely cause**: prompt latitude, or the policy text was unusually
  short and the model padded.
- **Fix**: tighten the extractor prompt; raise temperature to 0; verify
  every emitted criterion text against the parsed PDF text and drop any
  that fails.

## 2. missed_criterion

The agent did not evaluate a criterion that the gold set requires.

- **Where it lives**: criteria extraction.
- **Detector**: `set(gold_ids) - set(predicted_ids)`.
- **Likely cause**: nested structure (sub-criteria under exceptions) was
  flattened, or pdfplumber lost text in a multi-column layout.
- **Fix**: improve the parser, or change the prompt to explicitly extract
  exception clauses.

## 3. wrong_span_citation

A reported policy or chart citation has out-of-bounds offsets.

- **Where it lives**: criteria checker (cited an evidence span that does
  not exist) or extractor (policy span trusted incorrectly).
- **Detector**: bounds check in `citation_generator` and again in the
  failure-mode classifier.
- **Likely cause**: mixing up evidence ids; LLM emitting a substring that
  is not actually in the text.
- **Fix**: re-derive spans from text matches; refuse to cite an evidence
  id the patient does not have.

## 4. evidence_misread

The agent supported a claim with an evidence id that does not exist on
the patient.

- **Where it lives**: criteria checker.
- **Detector**: `cited_id not in {e.id for e in patient.evidence}`.
- **Likely cause**: model hallucinated an id like `E0099` when there are
  only 6 evidence items.
- **Fix**: pre-list evidence ids in the prompt and instruct the model to
  cite only from that list; the checker already filters but we can also
  hard-fail and ask again.

## 5. logical_error

Decision disagrees with gold and the agent's confidence was under 0.8.

- **Where it lives**: criteria checker or calibrator.
- **Detector**: `predicted != gold and confidence < 0.8`.
- **Severity**: medium. The model knew it was uncertain.
- **Fix**: most often a per-criterion call failed in a way the calibrator
  could not recover. Inspect the trace to see which criterion got the
  unexpected status.

## 6. calibration_failure

Decision disagrees with gold AND confidence is at least 0.8.

- **Severity**: high. The agent was confidently wrong.
- **Fix**: this is the regression test for the calibrator. If it
  reappears after a v2 isotonic-regression calibrator, that calibrator
  needs more training data.

## 7. latency_outlier

Wall-clock over 30 seconds.

- **Where it lives**: any node, but most often the criteria checker
  because it's `O(criteria)` LLM calls.
- **Fix**: batch criteria into fewer calls; cache results across
  reruns of the same gold case during development.

## Pipeline error

If a case fails to run at all (exception, network error), it is recorded
as `pipeline_error` and excluded from agreement / calibration metrics.
Investigate via the per-run JSON in `data/eval_results/`.
