"""Load Synthea-generated FHIR Bundles into the running backend.

Run scripts/generate_synthea.py first (or point Synthea at any output dir),
then this script ingests every Bundle JSON into the patients API.

Usage:
    python scripts/load_synthea_population.py \
        --dir data/patients/synthea/fhir \
        --limit 50

The Synthea FHIR exporter emits one file per patient. This script POSTs
each one to /patients (multipart) so it ends up in the same SQLite the
UI reads from.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="data/patients/synthea/fhir",
                        help="Synthea FHIR output directory")
    parser.add_argument("--backend", default="http://localhost:8000")
    parser.add_argument("--limit", type=int, default=50, help="Max patients to load")
    parser.add_argument("--api-key", default=None, help="X-API-Key if auth enabled")
    args = parser.parse_args(argv)

    src = (ROOT / args.dir).resolve() if not Path(args.dir).is_absolute() else Path(args.dir)
    if not src.is_dir():
        print(f"directory not found: {src}", file=sys.stderr)
        return 2

    headers = {"x-api-key": args.api_key} if args.api_key else {}
    files = sorted(src.glob("*.json"))[: args.limit]
    if not files:
        print(f"no .json files in {src}")
        return 1

    client = httpx.Client(timeout=120.0)
    ok = err = 0
    for i, path in enumerate(files, start=1):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[skip] {path.name}: not valid JSON ({exc})")
            err += 1
            continue
        if bundle.get("resourceType") != "Bundle":
            print(f"[skip] {path.name}: not a FHIR Bundle")
            err += 1
            continue

        # Stable patient_id from the Bundle's Patient resource id, fallback to file stem
        pid = path.stem
        for entry in bundle.get("entry", []):
            r = entry.get("resource") or {}
            if r.get("resourceType") == "Patient" and r.get("id"):
                pid = f"SYNTHEA-{r['id'][:8].upper()}"
                break

        try:
            r = client.post(
                f"{args.backend}/patients",
                json={"fhir_bundle": bundle, "patient_id": pid},
                headers=headers,
            )
            r.raise_for_status()
            d = r.json()
            print(f"[{i:3}/{len(files)}] {pid} | age {d['age']} | {len(d['evidence'])} evidence rows")
            ok += 1
        except Exception as exc:
            print(f"[err ] {path.name}: {exc}")
            err += 1

    print()
    print(f"done. loaded {ok}, errors {err}.")
    print("open http://localhost:3000/determine to use them")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
