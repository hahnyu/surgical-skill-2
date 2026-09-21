#!/usr/bin/env python3
"""Fail fast when the committed Phase 1 audit contradicts its manifests."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    expected_files = {
        "JIGSAWS": (16763, 893368730),
        "ROSMA": (413, 22207164939),
        "BGU-SKILLS": (22, 270172633854),
        "BGU-PatCut": (55, 408314079634),
    }
    summary = rows("data/manifests/dataset_files_summary.csv")
    observed = {
        row["dataset"]: (int(row["file_count"]), int(row["size_bytes"]))
        for row in summary
    }
    assert observed == expected_files, (observed, expected_files)

    manifest_specs = {
        "data/manifests/rosma_files.csv": (413, 22207164939),
        "data/manifests/bgu_skills_files.csv": (22, 270172633854),
        "data/manifests/bgu_patcut_files.csv": (55, 408314079634),
    }
    for relative, (count, total_bytes) in manifest_specs.items():
        manifest = rows(relative)
        assert len(manifest) == count, relative
        assert sum(int(row["size_bytes"]) for row in manifest) == total_bytes, relative
        assert all(row["provided_checksum"] for row in manifest), relative

    jigsaws = rows("data/manifests/jigsaws_inventory.csv")
    assert sum(int(row["file_count"]) for row in jigsaws) == 16763
    assert sum(int(row["size_bytes"]) for row in jigsaws) == 893368730
    assert all(len(row["tree_sha256"]) == 64 for row in jigsaws)

    source_hashes = rows("data/manifests/source_metadata_sha256.csv")
    for row in source_hashes:
        path = ROOT / row["path"]
        assert path.stat().st_size == int(row["size_bytes"]), path
        assert sha256(path) == row["sha256"], path

    counts = rows("reports/tables/trial_counts.csv")
    eligible = {}
    for row in counts:
        value = row["eligible_matched_trials"]
        if value.isdigit():
            eligible[(row["dataset"], row["task_or_stratum"])] = int(value)
    assert sum(value for (dataset, _), value in eligible.items() if dataset == "JIGSAWS") == 103
    assert sum(value for (dataset, _), value in eligible.items() if dataset == "ROSMA") == 206
    assert sum(value for (dataset, _), value in eligible.items() if dataset == "BGU-PatCut") == 1254

    rosma = rows("reports/tables/rosma_error_distribution.csv")
    assert sum(int(row["trials"]) for row in rosma) == 206
    assert sum(int(row["nonzero_error_trials"]) for row in rosma) == 61

    targets = rows("reports/tables/target_provenance.csv")
    assert all(row["primary_eligibility"] in {"eligible", "secondary", "ineligible"} for row in targets)
    assert {(row["dataset"], row["target"]) for row in targets if row["primary_eligibility"] == "eligible"} == {
        ("JIGSAWS", "GRS"),
        ("ROSMA", "Errors"),
        ("BGU-PatCut", "TE"),
    }

    report = (ROOT / "reports/feasibility_report.md").read_text(encoding="utf-8")
    assert "Plan A recommended" in report
    assert "No predictive model trained" in report
    print("Phase 1 validation passed")


if __name__ == "__main__":
    main()

