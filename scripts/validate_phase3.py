#!/usr/bin/env python3
"""Validate the Phase 3 baseline/audit acceptance gate."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

from surgical_skill2.audit import config_sha256


ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "results" / "predictions" / "private"
METRICS = ROOT / "results" / "metrics"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    config = yaml.safe_load((ROOT / "configs" / "experiments" / "phase3_baseline.yaml").read_text())
    expected_config_hash = config_sha256(config)
    expected_prediction_rows = {
        "phase3_performance": 13225,
        "phase3_identity_probes": 12505,
        "phase3_skill_permutations": 41303,
        "phase3_identity_null": 125050,
        "phase3_outcome_null": 156300,
    }
    artifacts = {row["artifact"]: row for row in rows(ROOT / "data" / "manifests" / "phase3_artifacts.csv")}
    commits = set()
    for name, expected_rows in expected_prediction_rows.items():
        path = PRIVATE / f"{name}.parquet"
        frame = pd.read_parquet(path)
        assert len(frame) == expected_rows, (name, len(frame))
        assert frame["trial_key"].notna().all()
        assert set(frame["config_sha256"]) == {expected_config_hash}
        commits.update(frame["git_commit"].unique())
        artifact = artifacts[f"private_{name}"]
        assert int(artifact["rows"]) == expected_rows
        assert artifact["sha256"] == sha256(path)
    assert len(commits) == 1 and next(iter(commits)).startswith("1008ee2"), commits

    performance_predictions = pd.read_parquet(PRIVATE / "phase3_performance.parquet")
    uniqueness = ["dataset", "task", "protocol", "target_name", "model", "trial_key"]
    assert not performance_predictions.duplicated(uniqueness).any()
    held = pd.read_csv(ROOT / "data" / "folds" / "held_out_participant.csv")
    assert (held.groupby(["dataset", "participant_key"])["test_fold"].nunique() == 1).all()

    identity = pd.read_csv(METRICS / "phase3_identity_probes.csv")
    raw = identity.loc[identity["model"].isin(["multinomial_logistic", "random_forest"])]
    assert len(raw) == 20
    assert (raw["balanced_accuracy"] > raw["permuted_identity_median_balanced_accuracy"]).all()
    assert (raw["empirical_p_value"] <= 0.05).all()

    skill_permutations = pd.read_csv(METRICS / "phase3_skill_permutation_summary.csv")
    assert len(skill_permutations) == 3
    assert (skill_permutations["participant_permutation_median"] > skill_permutations["record_permutation_median"]).all()
    assert (skill_permutations["empirical_p_participant_not_greater"] <= 0.01).all()

    outcome_null = pd.read_csv(METRICS / "phase3_outcome_null_summary.csv")
    assert len(outcome_null) == 7
    assert (outcome_null["median"] < 0).all()

    replication = pd.read_csv(METRICS / "phase3_paper1_replication.csv")
    assert len(replication) == 12
    assert replication["within_tolerance"].sum() == 11
    discrepancy = replication.loc[~replication["within_tolerance"]]
    assert discrepancy.iloc[0]["task"] == "Needle Passing"
    assert discrepancy.iloc[0]["protocol"] == "held_out_participant"

    canary = json.loads((METRICS / "phase3_leakage_canary.json").read_text())
    assert canary["forbidden_column_detected"] is True
    assert canary["canary_present_in_final_predictors"] is False
    assert all(row["one_hot_identity_accuracy"] == 1.0 for row in canary["positive_control"])

    for artifact in artifacts.values():
        if artifact["kind"] == "committed_aggregate":
            path = ROOT / artifact["path"]
            assert path.exists(), artifact
            assert sha256(path) == artifact["sha256"], path

    report = (ROOT / "reports" / "audit_report.md").read_text(encoding="utf-8")
    assert "X01_Pea_on_a_Peg_03" in report
    assert "1.8467" in report
    assert "No identity-suppression intervention" in report
    print("Phase 3 validation passed: OOF metrics, controls, canary, hashes, and replication checked")


if __name__ == "__main__":
    main()
