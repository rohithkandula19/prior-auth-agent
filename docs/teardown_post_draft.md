# Teardown: building a citation-grounded prior auth agent

This is a working draft of a public writeup. Not for publication yet.

## TL;DR

Prior auth is plausible territory for a Claude-based agent because the
work is high-volume, document-heavy, and structurally repetitive. Most
demos in this space show a chat that says "approved" or "denied". That is
not the interesting part. The interesting part is: where exactly in the
policy and the chart did the model find the answer, and how confident is
it that it found the right thing?

I built a small but realistic version of that, end to end:

- a payer policy goes in (synthetic UHC MRI Lumbar Spine for the demo)
- a FHIR R4 patient bundle goes in
- out comes a Determination with per-criterion verdicts, char-level
  citations into both policy and chart, a calibrated confidence, and any
  documentation gaps that block approval

You can navigate the result in a split-pane viewer that highlights every
cited span and links them across the two documents.

The repo: <https://github.com/rohithkandula19/prior-auth-agent>

## What I wanted to avoid

Three failure modes are common when LLMs read policies and charts:

1. **Plausible reasoning that does not match the source.** The model
   says "the patient had 8 weeks of PT" because it inferred that, not
   because the chart contains those words.
2. **Confidently wrong calls.** The model is just as sure when it is
   wrong as when it is right, so reviewers cannot triage by confidence.
3. **Output that is hard to audit.** Reviewers cannot quickly see why
   the model made the call, so they end up reading both documents
   themselves anyway.

The architecture pushes back on each of these.

## Verbatim everywhere

Both the criteria extractor and the evidence extractor are required to
emit text that is a substring of the source. I do not trust the model's
self-reported character offsets. Instead I take whatever text the model
emits, run `find()` on the parsed source, and use that index. If the text
does not match (the model paraphrased), the entry is dropped or kept with
a `(0, 0)` placeholder span and a warning. Reviewers see those warnings
in the metadata.

This is unglamorous and not novel, but it eliminates a whole class of
audit-breaking citations.

## Calibrator

Per-criterion confidences come from the model. The calibrator weighs
them (a `not_met` required criterion gets 2x weight because it is more
likely to drive the decision) and applies deterministic decision rules:
contraindication-met denies; all-required-met approves; any required
not-met denies; otherwise needs-more-info, with confidence capped at 0.6.

This is V1. V2 is an isotonic regression fit on the gold set, applied to
the V1 score. The eval dashboard already plots reliability bins so you
can see where the calibrator is over- or under-confident.

## The eval is the deliverable

It is easy to ship a demo that does well on three cases. The harness
makes it harder to lie to yourself:

- 7-mode failure taxonomy (hallucinated criterion, missed criterion,
  wrong span citation, evidence misread, logical error, calibration
  failure, latency outlier)
- Per-decision-class agreement so a model that always says "approved"
  cannot hide
- Reliability bins and ECE for calibration
- Latency p50/p95/p99 and per-case cost

The bootstrap gold set is 10 cases on a synthetic policy. The next pass
adds 100 hand-labeled cases across three real payer policies (UHC MRI
Lumbar, Aetna Humira, Cigna bariatric) plus 20 adversarial cases
(contradictory evidence, ambiguous criteria, wrong patient).

## The hero UI

The results page is two synchronized panes (policy left, chart right)
with every cited span highlighted. Clicking a span scrolls both panes to
the matching pair. A confidence meter, the recommended action, and any
documentation gaps sit above. The criterion checklist below shows the
status badge, reasoning, and supporting evidence ids for each criterion.

This is the only screen reviewers actually need to be productive. The
rest of the app exists to feed it.

## Stack

- Python 3.12, FastAPI, LangGraph
- Anthropic Claude or OpenRouter (Qwen, Llama, DeepSeek, Gemma) via a
  switchable client. The default for this writeup uses Qwen 2.5 72B
  Instruct because it is cheap, fast, and held up well on structured
  extraction.
- pdfplumber for policy parsing
- FAISS for per-policy criterion retrieval (currently built but not yet
  used at decision time; it becomes load-bearing once we route across
  many policies)
- Next.js 14, Tailwind 3 for the UI
- Cloud Run + Artifact Registry for deployment

## What is next

- Real policies and a real gold set.
- V2 calibrator with isotonic regression.
- Citation precision / recall scoring (currently the eval scores agreement
  and calibration but not citation quality directly).
- Postgres + pgvector behind the in-memory repos.
- Per-criterion batching to bring per-case cost down.

## Lessons

- Refuse to ship anything that does not survive `text.find()`. Plausible
  is not the same as correct.
- Build the eval before you tune the prompts. Otherwise you spend a week
  on prompt golf and have no way to know if it helped.
- Make the audit surface the hero, not an afterthought. The only people
  who matter for adoption are reviewers, and they cannot triage what
  they cannot see.
