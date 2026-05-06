"""Wrap the Synthea CLI to generate synthetic FHIR R4 patient bundles.

Synthea is a Java app: https://github.com/synthetichealth/synthea
This script assumes you have synthea-with-dependencies.jar somewhere on disk
and that `java` is on PATH. It writes FHIR Bundles to SYNTHEA_OUTPUT_DIR.

Usage:
    python scripts/generate_synthea.py \
        --jar /path/to/synthea-with-dependencies.jar \
        --population 25 \
        --module back_pain
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402

log = get_logger(__name__)


def run_synthea(jar: Path, population: int, module: str | None, out_dir: Path) -> int:
    if not jar.exists():
        log.error("synthea_jar_missing", path=str(jar))
        return 2
    if shutil.which("java") is None:
        log.error("java_not_on_path")
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "java",
        "-jar",
        str(jar),
        "-p",
        str(population),
        "--exporter.fhir.export",
        "true",
        "--exporter.baseDirectory",
        str(out_dir),
    ]
    if module:
        cmd += ["-m", module]

    log.info("synthea_run", cmd=cmd)
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--jar", required=True, type=Path)
    parser.add_argument("--population", type=int, default=10)
    parser.add_argument("--module", default=None)
    parser.add_argument("--out", type=Path, default=settings.synthea_output_dir)
    args = parser.parse_args(argv)
    return run_synthea(args.jar, args.population, args.module, args.out)


if __name__ == "__main__":
    sys.exit(main())
