# Architecture

## Goals

1. Read a payer medical policy and a patient chart, decide whether a
   procedure should be authorized, and cite the exact spans of policy and
   chart that support each call.
2. Make the decision auditable. Every claim is grounded in a verbatim span,
   and the eval harness scores citation precision and recall, not just
   decision agreement.
3. Make confidence calibrated, so reviewers can prioritize low-confidence
   determinations rather than treating all model output the same.

## Why this shape

A common failure mode for chart-and-policy LLMs is plausible-sounding
reasoning that does not match the underlying text. We push back on that in
three places:

1. **Verbatim-only criteria extraction.** The criteria extractor must emit
   text that is a substring of the parsed policy. We re-derive `char_span`
   from the substring position, not from model-reported offsets, so that
   any UI highlight is guaranteed to come from the source.
2. **Evidence with verbatim source_text.** Both the FHIR-driven chart
   parser (deterministic) and the narrative evidence extractor (LLM) carry
   a verbatim `source_text` that is found in `raw_chart` before the
   evidence is admitted.
3. **Citation verification node.** A separate graph node checks every
   policy and chart span for in-bounds offsets and drops invalid ones with
   a metric. Even if the criteria checker hallucinates a span, the audit
   surface stays clean.

## Data flow

### Ingestion

- `policy_parser.parse_pdf` uses pdfplumber and emits `[[PAGE n]]` markers
  so downstream char spans can be mapped to pages.
- `criteria_extractor.CriteriaExtractor` calls the LLM once per policy
  with a strict prompt and re-derives spans by `find()`-ing the model's
  text in the parsed PDF text. Non-verbatim criteria are kept but marked
  with `(0, 0)` spans and a warning so reviewers can spot them.
- `policy_indexer.build_policy` orchestrates parse, extract, embed (Voyage
  AI), and FAISS index build. Embeddings are optional for synthetic dev
  use (`--skip-embeddings`).

### Patient

- `chart_parser.parse_bundle` walks a FHIR R4 Bundle and emits one
  `ClinicalEvidence` per supported resource type (Patient, Condition,
  MedicationRequest, Procedure, Observation, DiagnosticReport). Each
  evidence carries a `source_text` line that is appended to `raw_chart`
  with a known offset, so spans match by construction.
- `evidence_extractor.EvidenceExtractor` is an optional LLM step that adds
  narrative facts. Same verbatim rule as the criteria extractor.

### Agent

A LangGraph `StateGraph` with one linear path:

```
START -> criteria_checker -> citation_generator -> gap_identifier -> calibrator -> END
```

- `criteria_checker` calls the LLM once per criterion with the criterion
  text, the criterion type, and the patient's evidence list. It returns
  `met | not_met | partial | insufficient_evidence` plus a confidence in
  `[0, 1]`.
- `citation_generator` validates span bounds and trims invalid citations.
- `gap_identifier` runs only when at least one criterion is
  `insufficient_evidence`, asking the LLM what specific clinical fact, if
  added, would change the determination.
- `calibrator` aggregates per-criterion confidence with weights (a
  `not_met` criterion gets 2x weight) and applies the decision rules. It
  caps the score at 0.6 when the decision is `needs_more_info`.

### API

In-memory repositories (`storage/repo.py`) back the v0 API. The interface
is simple enough that a Postgres-backed implementation can drop in without
touching routes.

### Frontend

- `/policies` and `/determine` are the operator entry points.
- `/results/[id]` is the hero. Two synchronized panes (policy on left,
  chart on right) highlight every cited span. Clicking a span scrolls
  both panes to the matching pair and outlines the active citation.
- `/eval` shows the latest harness summary, with reliability bins,
  latency percentiles, and a failure-mode breakdown.

## Why a linear graph instead of a true supervisor

The architecture spec mentions a supervisor topology with four parallel
workers. We considered that but the four nodes have hard dependencies:
citation verification needs the checker output, gap analysis needs to know
which criteria came back insufficient, and the calibrator needs everything.
Running them in parallel would either duplicate the LLM calls or introduce
synchronization complexity for no quality gain. A linear `StateGraph` keeps
the audit trace simple and makes per-node cost easy to attribute.

## Trade-offs and known limits

- **Cost grows with criterion count.** One LLM call per criterion is fine
  for typical policies (5-30 criteria) but expensive for very long ones.
  A future optimization is to batch related criteria into one prompt and
  parse a list response.
- **In-memory store** is fine for the demo but loses state on restart.
  Persistence is in scope for the next iteration.
- **Calibration is rule-based v1.** A v2 isotonic regression fit on a
  larger gold set is sketched in the calibrator docstring.
- **No retrieval at decision time yet.** The FAISS index is built but not
  used by the agent (we feed all criteria to the checker directly). It
  becomes load-bearing once policies grow past a few thousand criteria
  combined or we want to dispatch to one of many policies automatically.
