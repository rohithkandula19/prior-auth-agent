PY := /opt/homebrew/bin/python3.12
VENV := .venv
ACT := . $(VENV)/bin/activate

.PHONY: venv install run test lint fmt clean ingest

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(ACT) && pip install --upgrade pip && pip install -r backend/requirements.txt

run:
	$(ACT) && uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0 --port 8000

test:
	$(ACT) && pytest backend/tests -v

lint:
	$(ACT) && ruff check backend

fmt:
	$(ACT) && ruff format backend

ingest:
	$(ACT) && python -m app.ingestion.policy_indexer --policy data/policies/uhc_mri_lumbar.pdf

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
