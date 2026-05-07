"""Seed the local backend with the three synthetic policies and three patients.

Useful right after a fresh install or after wiping data/priorauth.db. Calls
the running backend on http://localhost:8000 (override with --backend).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent

POLICIES = [
    {
        "policy_id": "uhc_mri_lumbar",
        "payer": "UnitedHealthcare",
        "procedure_code": "72148",
        "procedure_name": "MRI Lumbar Spine",
        "effective_date": "2025-01-01",
        "source_url": "synthetic",
        "text_path": "data/policies/uhc_mri_lumbar_synthetic.txt",
    },
    {
        "policy_id": "aetna_humira",
        "payer": "Aetna",
        "procedure_code": "J0135",
        "procedure_name": "Adalimumab (Humira) for Rheumatoid Arthritis",
        "effective_date": "2025-01-01",
        "source_url": "synthetic",
        "text_path": "data/policies/aetna_humira_synthetic.txt",
    },
    {
        "policy_id": "cigna_bariatric",
        "payer": "Cigna",
        "procedure_code": "43644",
        "procedure_name": "Bariatric Surgery",
        "effective_date": "2025-01-01",
        "source_url": "synthetic",
        "text_path": "data/policies/cigna_bariatric_synthetic.txt",
    },
]

PATIENTS = [
    ("data/patients/sample_back_pain.json", "SYNTH-1042"),
    ("data/patients/sample_ra.json", "SYNTH-2034"),
    ("data/patients/sample_bariatric.json", "SYNTH-3081"),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="http://localhost:8000")
    args = parser.parse_args(argv)

    client = httpx.Client(timeout=300.0)

    for p in POLICIES:
        text = (ROOT / p["text_path"]).read_text(encoding="utf-8")
        body = {**p, "text": text, "skip_embeddings": True}
        body.pop("text_path", None)
        print(f"[policy] ingesting {p['policy_id']}")
        r = client.post(f"{args.backend}/policies/ingest_text", json=body)
        r.raise_for_status()
        d = r.json()
        print(f"  -> {d['id']} | {len(d['criteria'])} criteria")

    for path, pid in PATIENTS:
        bundle = json.loads((ROOT / path).read_text(encoding="utf-8"))
        print(f"[patient] ingesting {pid}")
        r = client.post(
            f"{args.backend}/patients", json={"fhir_bundle": bundle, "patient_id": pid}
        )
        r.raise_for_status()
        d = r.json()
        print(f"  -> {d['id']} | age {d['age']} | {len(d['evidence'])} evidence rows")

    print("done. open http://localhost:3000/policies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
