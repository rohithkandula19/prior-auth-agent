# Prior Authorization Agent

AI agent that reads payer medical policies and patient charts, then produces citation-grounded prior authorization decisions with calibrated confidence scores and a full eval harness.

## Stack

- Python 3.12, FastAPI, LangGraph, Anthropic Claude
- FAISS for policy retrieval, pgvector optional for persistence
- Next.js 14 with Tailwind for the UI
- Cloud Run target deployment via Artifact Registry

## Quick start

```bash
make install
cp .env.example .env  # fill in ANTHROPIC_API_KEY
make run
```

Open http://localhost:8000/docs.

## Layout

- `backend/app/` FastAPI app, agent graph, ingestion, eval
- `frontend/` Next.js UI
- `data/policies/` raw payer PDFs
- `data/gold_set/` manually labeled determinations
- `scripts/` ingestion and eval CLIs
- `docs/` architecture and methodology notes

## Build status

Initial scaffold. See `docs/architecture.md` for the full design.

## House rules

- No em dashes anywhere in code, comments, docs, or UI copy.
- Python venv at `/opt/homebrew/bin/python3.12`.
- Container images pushed to Artifact Registry, never gcr.io.
