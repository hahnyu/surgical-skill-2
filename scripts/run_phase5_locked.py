#!/usr/bin/env python3
"""Regenerate and verify the complete locked Phase 5 analysis."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = Path(sys.executable)


def run(*args: str) -> None:
    subprocess.run([str(PYTHON), *args], cwd=ROOT, check=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    for phase in range(1, 5):
        run(f"scripts/validate_phase{phase}.py")
    run("scripts/summarize_phase3.py")
    run("scripts/summarize_phase4.py")
    run("scripts/build_phase5_analysis.py")
    manifest = ROOT / "data" / "manifests" / "phase5_artifacts.csv"
    first = digest(manifest)
    run("scripts/build_phase5_analysis.py")
    second = digest(manifest)
    if first != second:
        raise RuntimeError(f"Phase 5 rerun hash mismatch: {first} != {second}")
    run("-m", "pytest", "-q")
    run("scripts/validate_phase5.py")
    print(f"Phase 5 locked rerun passed; manifest SHA-256={second}")


if __name__ == "__main__":
    main()
