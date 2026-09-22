#!/usr/bin/env python3
"""Validate the complete Phase 2 preprocessing gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_fold_file(path: Path, feature_trials: set[str], held_out: bool) -> None:
    rows = csv_rows(path)
    assert len(rows) == 2501, (path, len(rows))
    assert len({row["trial_key"] for row in rows}) == len(rows), path
    assert {row["trial_key"] for row in rows} == feature_trials, path
    assert set(rows[0]) == {
        "dataset", "task", "protocol", "test_fold", "trial_key", "participant_key"
    }

    participant_folds: dict[tuple[str, str], set[str]] = defaultdict(set)
    task_participant_folds: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        participant_folds[(row["dataset"], row["participant_key"])].add(row["test_fold"])
        task_participant_folds[(row["dataset"], row["task"], row["participant_key"])].add(row["test_fold"])

    if held_out:
        assert all(len(folds) == 1 for folds in participant_folds.values())
        for dataset in {row["dataset"] for row in rows}:
            dataset_rows = [row for row in rows if row["dataset"] == dataset]
            for fold in {row["test_fold"] for row in dataset_rows}:
                test_people = {row["participant_key"] for row in dataset_rows if row["test_fold"] == fold}
                train_people = {row["participant_key"] for row in dataset_rows if row["test_fold"] != fold}
                assert test_people.isdisjoint(train_people), (dataset, fold)
    else:
        assert all(len(folds) >= 2 for folds in task_participant_folds.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rerun",
        type=Path,
        default=ROOT / "data" / "processed" / "private" / "phase2_features_rerun.csv",
        help="independently regenerated feature file that must match the canonical hash",
    )
    args = parser.parse_args()

    canonical = ROOT / "data" / "processed" / "private" / "phase2_features.csv"
    features = pd.read_csv(canonical, na_values=["NA"])
    expected_counts = {
        ("BGU-PatCut", "Pattern Cutting"): 1254,
        ("BGU-SKILLS", "Knot Tying"): 311,
        ("BGU-SKILLS", "Ring Tower Transfer"): 312,
        ("BGU-SKILLS", "Suturing"): 315,
        ("JIGSAWS", "Knot Tying"): 36,
        ("JIGSAWS", "Needle Passing"): 28,
        ("JIGSAWS", "Suturing"): 39,
        ("ROSMA", "Pea on a Peg"): 71,
        ("ROSMA", "Post and Sleeve"): 65,
        ("ROSMA", "Wire Chaser I"): 70,
    }
    observed_counts = features.groupby(["dataset", "task"]).size().to_dict()
    assert observed_counts == expected_counts, (observed_counts, expected_counts)
    assert len(features) == 2501
    assert features["trial_key"].nunique() == 2501
    assert features.groupby("dataset")["participant_key"].nunique().to_dict() == {
        "BGU-PatCut": 54, "BGU-SKILLS": 18, "JIGSAWS": 8, "ROSMA": 12,
    }
    assert features["source_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()

    required_numeric = [
        column for column in features.columns
        if column.endswith(("_m", "_m_s", "_m_s2", "_m_s3", "_fraction", "_m3", "_sampling_hz"))
        or column in {"duration_s", "bimanual_speed_correlation", "path_length_asymmetry"}
    ]
    assert not features[required_numeric].isna().any().any()
    assert (features["duration_s"] > 0).all()
    assert features["bimanual_speed_correlation"].between(-1, 1).all()

    feature_trials = set(features["trial_key"])
    validate_fold_file(ROOT / "data" / "folds" / "same_participant.csv", feature_trials, False)
    validate_fold_file(ROOT / "data" / "folds" / "held_out_participant.csv", feature_trials, True)

    artifacts = {row["artifact"]: row for row in csv_rows(ROOT / "data" / "manifests" / "phase2_artifacts.csv")}
    canonical_hash = sha256(canonical)
    assert artifacts["private_harmonized_features"]["sha256"] == canonical_hash
    assert artifacts["same_participant_folds"]["sha256"] == sha256(ROOT / "data" / "folds" / "same_participant.csv")
    assert artifacts["held_out_participant_folds"]["sha256"] == sha256(ROOT / "data" / "folds" / "held_out_participant.csv")
    assert args.rerun.exists(), f"missing independent rerun: {args.rerun}"
    assert sha256(args.rerun) == canonical_hash, "feature rerun differs from canonical extraction"
    print(f"Phase 2 validation passed: 2501 trials; reproducible SHA-256 {canonical_hash}")


if __name__ == "__main__":
    main()
