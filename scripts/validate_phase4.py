#!/usr/bin/env python3
"""Validate the Phase 4 intervention acceptance gate."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from surgical_skill2.audit import config_sha256


PRIVATE = ROOT / "results" / "predictions" / "private"
METRICS = ROOT / "results" / "metrics"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    config = yaml.safe_load(
        (ROOT / "configs" / "experiments" / "phase4_interventions.yaml").read_text()
    )
    expected_hash = config_sha256(config)
    expected = {
        "phase4_linear_task": (15630, "93b10a3"),
        "phase4_linear_probes": (25010, "93b10a3"),
        "phase4_linear_selection": (144, "93b10a3"),
        "phase4_adversarial_task": (28134, "28d0cbe"),
        "phase4_adversarial_probes": (28134, "28d0cbe"),
        "phase4_adversarial_selection": (126, "28d0cbe"),
        "phase4_skill": (1442, "019b9ae"),
    }
    artifacts = {
        row["artifact"]: row
        for row in csv_rows(ROOT / "data" / "manifests" / "phase4_artifacts.csv")
    }
    for name, (expected_rows, commit_prefix) in expected.items():
        path = PRIVATE / f"{name}.parquet"
        frame = pd.read_parquet(path)
        assert len(frame) == expected_rows, (name, len(frame))
        assert set(frame["config_sha256"]) == {expected_hash}
        assert len(frame["git_commit"].unique()) == 1
        assert frame["git_commit"].iloc[0].startswith(commit_prefix)
        artifact = artifacts[f"private_{name}"]
        assert int(artifact["rows"]) == expected_rows
        assert artifact["sha256"] == sha256(path)

    uniqueness = ["dataset", "task", "protocol", "intervention", "model", "seed", "trial_key"]
    for name in [
        "phase4_linear_task", "phase4_linear_probes", "phase4_adversarial_task",
        "phase4_adversarial_probes", "phase4_skill",
    ]:
        frame = pd.read_parquet(PRIVATE / f"{name}.parquet")
        assert not frame.duplicated(uniqueness).any(), name
        assert frame["trial_key"].notna().all(), name
        assert not any("canary" in str(column).lower() for column in frame.columns)

    linear_selection = pd.read_parquet(PRIVATE / "phase4_linear_selection.parquet")
    adversarial_selection = pd.read_parquet(PRIVATE / "phase4_adversarial_selection.parquet")
    assert not linear_selection.duplicated(["dataset", "task", "protocol", "test_fold"]).any()
    assert not adversarial_selection.duplicated(["dataset", "task", "protocol", "test_fold"]).any()
    assert (linear_selection["selected_k"] >= 0).all()
    assert (linear_selection["selected_k"] <= max(config["linear"]["identity_k_grid"])).all()
    assert set(adversarial_selection["selected_lambda"]).issubset(set(config["adversarial"]["lambda_grid"]))
    for payload in linear_selection["selection_json"]:
        assert "0" in json.loads(payload)
    for payload in adversarial_selection["selection_json"]:
        assert "0.0" in json.loads(payload)

    primary = pd.read_csv(METRICS / "phase4_primary_comparison.csv")
    i3 = primary.loc[primary["candidate"] == "I3_identity_subspace"]
    i4 = primary.loc[primary["candidate"] == "I4_adversarial"]
    assert len(i3) == 2 and i3["probe_endpoint_passed"].all()
    assert (i3["ci_high"] < 0).all() and i3["candidate_verified"].all()
    assert i3["designated_primary"].all()
    assert len(i4) == 2 and not i4["candidate_verified"].any()
    assert not i4.loc[i4["probe_model"] == "nonlinear_probe", "probe_endpoint_passed"].iloc[0]

    ablation = pd.read_csv(METRICS / "phase4_ablation_log.csv")
    random_vs_i3 = ablation.loc[
        (ablation["candidate"] == "random_projection")
        & (ablation["baseline"] == "I3_identity_subspace")
    ].iloc[0]
    assert random_vs_i3["linear_probe_mean_difference"] > 0
    assert random_vs_i3["nonlinear_probe_mean_difference"] > 0
    assert len(pd.read_csv(METRICS / "phase4_skill_performance.csv")) == 42
    assert len(pd.read_csv(METRICS / "phase4_task_performance.csv")) == 196

    for artifact in artifacts.values():
        if artifact["kind"] == "committed_aggregate":
            path = ROOT / artifact["path"]
            assert path.exists(), artifact
            assert sha256(path) == artifact["sha256"], path

    report = (ROOT / "reports" / "intervention_report.md").read_text(encoding="utf-8")
    assert "I3_identity_subspace" in report
    assert "−0.184" in report
    assert "Phase 5" in report
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    status = re.search(r"Phases 0–(\d+) are complete", readme)
    assert status and int(status.group(1)) >= 4
    print("Phase 4 validation passed: interventions, controls, OOF rows, hashes, and primary decision checked")


if __name__ == "__main__":
    main()
