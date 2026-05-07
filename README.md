# Prior Authorization Agent

AI agent that reads payer medical policies and patient charts, then produces
citation-grounded prior authorization decisions with calibrated confidence
scores and a full eval harness.

The hero output: a determination page that shows the policy and chart with
every cited span highlighted, plus a "what would flip this?" counterfactual
panel and a one-click appeal letter generator. A reviewer can audit, act,
or appeal in seconds rather than minutes.

## Surfaces

- **Pre-check** (provider-side wedge): paste a draft note, get the list of
  things to add before submitting.
- **Determine**: full agent run with live progress streaming.
- **Results**: split-pane citation viewer, criteria checklist, appeal letter
  drafting, counterfactual analysis, PDF export.
- **Queue** (payer-side wedge): all determinations triaged into auto-clear /
  reviewer / escalate lanes by confidence.
- **Eval**: gold-set agreement, calibration curve, citation precision/recall,
  failure-mode taxonomy, A/B model comparison.
- **Audit**: append-only log of every PHI-touching request.

## Stack

- Python 3.12, FastAPI, LangGraph
- LLM: Anthropic Claude or OpenRouter (Qwen, Llama, DeepSeek, Gemma) via a
  switchable client
- FAISS for per-policy criterion retrieval; Postgres + pgvector optional
- Next.js 14, Tailwind 3 for the UI
- Cloud Run deployment through Artifact Registry

## Quick start

```bash
# 1. backend
make install                # python3.12 venv + deps
cp .env.example .env        # set ANTHROPIC_API_KEY or OPENROUTER_API_KEY
make run                    # uvicorn on :8000

# 2. frontend (in a second shell)
cd frontend && npm install && npm run dev   # next on :3000
```

Open <http://localhost:3000>. The API docs are at
<http://localhost:8000/docs>.

### Switching LLM providers

```bash
# Anthropic (default)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# OpenRouter
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=qwen/qwen-2.5-72b-instruct
```

The `ClaudeClient` wrapper at `backend/app/core/llm.py` dispatches to either
backend; the rest of the codebase is provider-agnostic.

## Pipeline

```
PDF policy ──> parse_pdf ──> Claude criteria_extractor ──> Policy + FAISS index
FHIR Bundle ──> parse_bundle ──> Patient (raw_chart + ClinicalEvidence)

      Patient + Policy
            │
            ▼
   ┌─────────────────────┐
   │  criteria_checker   │   per-criterion status + confidence
   └────────┬────────────┘
            ▼
   ┌─────────────────────┐
   │  citation_generator │   verifies span bounds
   └────────┬────────────┘
            ▼
   ┌─────────────────────┐
   │  gap_identifier     │   only when status == insufficient_evidence
   └────────┬────────────┘
            ▼
   ┌─────────────────────┐
   │  calibrator         │   decision rules + weighted confidence
   └────────┬────────────┘
            ▼
       Determination
```

Decision rules in the calibrator:

1. Any contraindication with `status == "met"` -> `denied`.
2. All required criteria `met` -> `approved`.
3. Any required criterion `not_met` -> `denied`.
4. Otherwise -> `needs_more_info`, confidence capped at 0.6.

## Eval

```bash
make ingest                            # one example policy
PYTHONPATH=backend .venv/bin/python scripts/run_eval.py --stub
```

The harness reports agreement vs gold, calibration (reliability bins, ECE),
latency p50/p95/p99, average cost, and a 7-mode failure taxonomy
(hallucinated criterion, missed criterion, wrong span citation, evidence
misread, logical error, calibration failure, latency outlier). See
[docs/eval_methodology.md](docs/eval_methodology.md).

## Ingesting a real payer policy

Public payer policies are linked off each plan's provider portal. Once you
have the PDF (URL or local file), use the helper:

```bash
# from a public URL
python scripts/ingest_real_policy.py \
    --url https://www.uhcprovider.com/.../mri-lumbar-spine.pdf \
    --policy-id uhc_mri_lumbar \
    --payer UnitedHealthcare \
    --procedure-code 72148 \
    --procedure-name "MRI Lumbar Spine"

# or from a local file
python scripts/ingest_real_policy.py \
    --file ~/Downloads/UHC_MRI_Lumbar_2025.pdf \
    --policy-id uhc_mri_lumbar --payer UnitedHealthcare \
    --procedure-code 72148 --procedure-name "MRI Lumbar Spine"
```

It calls `POST /policies/ingest` (multipart) so the result lands in the
same SQLite/Postgres the UI reads from.

## Layout

```
backend/app/
  agent/          LangGraph supervisor + 4 nodes + prompts
  api/            FastAPI route modules
  core/           LLM client, embeddings, structlog
  eval/           Harness, metrics, failure-mode classifier
  extraction/     FHIR Bundle to Patient, narrative evidence extractor
  ingestion/      PDF parser, criteria extractor, FAISS indexer
  schemas/        Pydantic models (Policy, Patient, Determination)
  storage/        FAISS wrapper, in-memory repos
frontend/
  app/            Next.js routes (/policies, /determine, /results/[id], /eval)
  components/     CitationViewer, CriteriaChecklist, ConfidenceMeter, ...
data/
  policies/       Raw PDFs and parsed JSON
  patients/       FHIR Bundles
  gold_set/       Labeled determinations (jsonl)
scripts/          Ingestion CLI, Synthea wrapper, eval runner
infra/            Dockerfiles, Cloud Build config, deploy.sh
docs/             architecture.md, eval_methodology.md, teardown_post_draft.md
```

## Deploy (Cloud Run via Artifact Registry)

```bash
PROJECT_ID=rotune-493315 REGION=us-central1 ./infra/deploy.sh
```

The script creates the `priorauth` repo if needed and submits Cloud Build,
which builds and deploys both services. Secrets `ANTHROPIC_API_KEY` and
`OPENROUTER_API_KEY` must exist in Secret Manager.

## House rules

- No em dashes anywhere in code, comments, docs, or UI copy.
- Python venv at `/opt/homebrew/bin/python3.12`.
- Container images pushed to Artifact Registry, never gcr.io.

## License

Synthetic policies and patients only by default. No real PHI is committed.
