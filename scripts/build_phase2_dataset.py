#!/usr/bin/env python3
"""Extract harmonized features, pseudonymous folds, and descriptive tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from surgical_skill2.features import extract_features
from surgical_skill2.folds import (
    held_out_participant_assignments,
    same_participant_assignments,
    validate_held_out,
    validate_same_participant,
)
from surgical_skill2.loaders import bgu_patcut, bgu_skills, jigsaws, rosma


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame = frame.sort_values(["dataset", "task", "participant_key", "trial_key"], kind="mergesort")
    frame.to_csv(path, index=False, float_format="%.12g", na_rep="NA", lineterminator="\n")


def write_folds(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["dataset", "task", "protocol", "test_fold", "trial_key", "participant_key"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def descriptives(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    output = []
    for (dataset, task), group in frame.groupby(["dataset", "task"], sort=True):
        outcome = group["outcome_value"].dropna()
        output.append(
            {
                "dataset": dataset,
                "task": task,
                "trials": len(group),
                "participants": group["participant_key"].nunique(),
                "duration_min_s": group["duration_s"].min(),
                "duration_median_s": group["duration_s"].median(),
                "duration_max_s": group["duration_s"].max(),
                "sampling_hz_median": pd.concat([group["psm1_sampling_hz"], group["psm2_sampling_hz"]]).median(),
                "outcome_name": group["outcome_name"].dropna().iloc[0] if group["outcome_name"].notna().any() else "none",
                "outcome_min": outcome.min() if len(outcome) else float("nan"),
                "outcome_median": outcome.median() if len(outcome) else float("nan"),
                "outcome_max": outcome.max() if len(outcome) else float("nan"),
            }
        )
    return pd.DataFrame(output)


def load_all() -> list:
    datasets = [
        ("JIGSAWS", lambda: jigsaws.iter_trials(ROOT / "data" / "raw" / "jigsaws")),
        ("ROSMA", lambda: rosma.iter_trials(ROOT / "data" / "raw" / "rosma")),
        ("BGU-SKILLS", lambda: bgu_skills.iter_trials(ROOT / "data" / "raw" / "bgu_skills")),
        ("BGU-PatCut", lambda: bgu_patcut.iter_trials(ROOT / "data" / "raw" / "bgu_patcut")),
    ]
    trials = []
    for name, loader in datasets:
        loaded = loader()
        trials.extend(loaded)
        print(f"Loaded {name}: {len(loaded)} trials", flush=True)
    return trials


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-output", type=Path, default=ROOT / "data" / "processed" / "private" / "phase2_features.csv")
    parser.add_argument("--write-public", action="store_true")
    args = parser.parse_args()

    trials = load_all()
    rows = []
    for index, trial in enumerate(trials, 1):
        rows.append(extract_features(trial))
        if index % 100 == 0 or index == len(trials):
            print(f"Features {index}/{len(trials)}", flush=True)
    if len(rows) != 2501:
        raise ValueError(f"expected 2501 harmonized rows, got {len(rows)}")
    write_rows(args.private_output, rows)
    print(f"Feature SHA-256: {sha256(args.private_output)}", flush=True)

    if args.write_public:
        same = same_participant_assignments(rows)
        held = held_out_participant_assignments(rows)
        validate_same_participant(same)
        validate_held_out(held)
        write_folds(ROOT / "data" / "folds" / "same_participant.csv", same)
        write_folds(ROOT / "data" / "folds" / "held_out_participant.csv", held)
        description = descriptives(rows)
        description.to_csv(
            ROOT / "reports" / "tables" / "phase2_dataset_descriptives.csv",
            index=False, float_format="%.12g", na_rep="NA", lineterminator="\n",
        )
        artifact_rows = [
            {
                "artifact": "private_harmonized_features",
                "rows": len(rows),
                "sha256": sha256(args.private_output),
                "contains_source_identifiers": "no; pseudonymous keys only",
                "redistribution": "not committed; regenerate from authorized/public sources",
            },
            {
                "artifact": "same_participant_folds",
                "rows": len(same),
                "sha256": sha256(ROOT / "data" / "folds" / "same_participant.csv"),
                "contains_source_identifiers": "no; pseudonymous keys only",
                "redistribution": "committed",
            },
            {
                "artifact": "held_out_participant_folds",
                "rows": len(held),
                "sha256": sha256(ROOT / "data" / "folds" / "held_out_participant.csv"),
                "contains_source_identifiers": "no; pseudonymous keys only",
                "redistribution": "committed",
            },
        ]
        with (ROOT / "data" / "manifests" / "phase2_artifacts.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(artifact_rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(artifact_rows)


if __name__ == "__main__":
    main()
