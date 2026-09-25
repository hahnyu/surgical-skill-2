#!/usr/bin/env python3
"""Derive every Phase 3 aggregate from saved out-of-fold predictions."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr
from sklearn.metrics import balanced_accuracy_score, f1_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from surgical_skill2.audit import classification_metrics, config_sha256, stable_seed


PRIVATE = ROOT / "results" / "predictions" / "private"
METRICS = ROOT / "results" / "metrics"
CONFIG_PATH = ROOT / "configs" / "experiments" / "phase3_baseline.yaml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def interval(values: np.ndarray, replicates: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(replicates, len(values)))
    estimates = values[indices].mean(axis=1)
    return tuple(np.quantile(estimates, [0.025, 0.975]))


def participant_average(frame: pd.DataFrame, values: np.ndarray) -> tuple[float, np.ndarray]:
    work = frame[["participant_key"]].copy()
    work["value"] = values
    participant_values = work.groupby("participant_key", sort=True)["value"].mean().to_numpy()
    return float(participant_values.mean()), participant_values


def summarize_performance(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_parquet(PRIVATE / "phase3_performance.parquet")
    replicates = int(config["uncertainty"]["participant_bootstrap_replicates"])
    rows = []
    groups = ["dataset", "task", "protocol", "target_name", "intervention", "model"]
    for key, group in frame.groupby(groups, sort=True, dropna=False):
        record = dict(zip(groups, key, strict=True))
        record["trials"] = len(group)
        record["participants"] = group["participant_key"].nunique()
        if record["target_name"] == "self_declared_skill":
            metrics = classification_metrics(group)
            correctness = (group["y_true"].astype(str) == group["y_pred"].astype(str)).to_numpy(dtype=float)
            estimate, values = participant_average(group, correctness)
            low, high = interval(values, replicates, stable_seed(config["seed"], *key, "accuracy"))
            record.update(metrics)
            record.update({"participant_average_metric": estimate, "metric_name": "accuracy", "ci_low": low, "ci_high": high})
            record.update({"mae": np.nan, "rmse": np.nan, "spearman": np.nan})
        else:
            truth = group["y_true"].astype(float).to_numpy()
            prediction = group["y_pred"].astype(float).to_numpy()
            absolute_error = np.abs(truth - prediction)
            estimate, values = participant_average(group, absolute_error)
            low, high = interval(values, replicates, stable_seed(config["seed"], *key, "mae"))
            record.update({
                "mae": float(absolute_error.mean()),
                "rmse": float(np.sqrt(np.mean((truth - prediction) ** 2))),
                "spearman": float(spearmanr(truth, prediction).statistic) if np.std(prediction) else np.nan,
                "participant_average_metric": estimate, "metric_name": "mae", "ci_low": low, "ci_high": high,
                "accuracy": np.nan, "balanced_accuracy": np.nan, "macro_f1": np.nan, "log_loss": np.nan,
            })
        rows.append(record)
    performance = pd.DataFrame(rows).sort_values(groups, kind="mergesort")

    gaps = []
    join_keys = ["dataset", "task", "target_name", "model", "participant_key", "trial_key"]
    same = frame.loc[frame["protocol"] == "same_participant"]
    held = frame.loc[frame["protocol"] == "held_out_participant"]
    paired = same.merge(held, on=join_keys, suffixes=("_same", "_held"), validate="one_to_one")
    for key, group in paired.groupby(["dataset", "task", "target_name", "model"], sort=True):
        dataset, task, target_name, model = key
        if target_name == "self_declared_skill":
            values = (
                (group["y_true_same"].astype(str) == group["y_pred_same"].astype(str)).astype(float)
                - (group["y_true_held"].astype(str) == group["y_pred_held"].astype(str)).astype(float)
            ).to_numpy()
            metric = "same_minus_held_accuracy"
        else:
            truth = group["y_true_same"].astype(float).to_numpy()
            same_error = np.abs(truth - group["y_pred_same"].astype(float).to_numpy())
            held_error = np.abs(truth - group["y_pred_held"].astype(float).to_numpy())
            values = held_error - same_error
            metric = "held_minus_same_mae"
        estimate, participant_values = participant_average(group, values)
        low, high = interval(participant_values, replicates, stable_seed(config["seed"], *key, "gap"))
        gaps.append({
            "dataset": dataset, "task": task, "target_name": target_name, "model": model,
            "metric": metric, "estimate": estimate, "ci_low": low, "ci_high": high,
            "participants": group["participant_key"].nunique(), "trials": len(group),
        })
    return performance, pd.DataFrame(gaps)


def summarize_identity(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    probes = pd.read_parquet(PRIVATE / "phase3_identity_probes.parquet")
    null = pd.read_parquet(PRIVATE / "phase3_identity_null.parquet")
    replicates = int(config["uncertainty"]["participant_bootstrap_replicates"])
    null_rows = []
    for (dataset, task, permutation), group in null.groupby(["dataset", "task", "permutation"], sort=True):
        metrics = classification_metrics(group)
        null_rows.append({"dataset": dataset, "task": task, "permutation": int(permutation), **metrics})
    null_metrics = pd.DataFrame(null_rows)

    rows = []
    for (dataset, task, model), group in probes.groupby(["dataset", "task", "model"], sort=True):
        metrics = classification_metrics(group)
        correctness = (group["y_true"].astype(str) == group["y_pred"].astype(str)).to_numpy(dtype=float)
        participant_balanced, values = participant_average(group, correctness)
        low, high = interval(values, replicates, stable_seed(config["seed"], dataset, task, model, "identity"))
        task_null = null_metrics.loc[(null_metrics["dataset"] == dataset) & (null_metrics["task"] == task)]
        median_null = float(task_null["balanced_accuracy"].median())
        p_value = float((1 + (task_null["balanced_accuracy"] >= metrics["balanced_accuracy"]).sum()) / (1 + len(task_null)))
        rows.append({
            "dataset": dataset, "task": task, "model": model,
            "trials": len(group), "participants": group["participant_key"].nunique(),
            **metrics, "participant_average_accuracy": participant_balanced,
            "balanced_accuracy_ci_low": low, "balanced_accuracy_ci_high": high,
            "permuted_identity_median_balanced_accuracy": median_null,
            "balanced_accuracy_minus_null": metrics["balanced_accuracy"] - median_null,
            "empirical_p_value": p_value,
        })
    return pd.DataFrame(rows), null_metrics


def summarize_skill_permutations() -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_parquet(PRIVATE / "phase3_skill_permutations.parquet")
    rows = []
    for (task, permutation_type, permutation), group in frame.groupby(
        ["task", "permutation_type", "permutation"], sort=True
    ):
        rows.append({
            "task": task, "permutation_type": permutation_type, "permutation": int(permutation),
            "accuracy": float((group["y_true"].astype(str) == group["y_pred"].astype(str)).mean()),
            "balanced_accuracy": float(balanced_accuracy_score(group["y_true"].astype(str), group["y_pred"].astype(str))),
            "macro_f1": float(f1_score(group["y_true"].astype(str), group["y_pred"].astype(str), average="macro", zero_division=0)),
        })
    distribution = pd.DataFrame(rows)
    summary = []
    for task, group in distribution.groupby("task", sort=True):
        observed = float(group.loc[group["permutation_type"] == "observed", "accuracy"].iloc[0])
        participant = group.loc[group["permutation_type"] == "participant_wise"].set_index("permutation")["accuracy"]
        record = group.loc[group["permutation_type"] == "record_wise"].set_index("permutation")["accuracy"]
        paired = participant - record
        summary.append({
            "task": task, "observed_accuracy": observed,
            "participant_permutation_median": float(participant.median()),
            "participant_permutation_q025": float(participant.quantile(0.025)),
            "participant_permutation_q975": float(participant.quantile(0.975)),
            "record_permutation_median": float(record.median()),
            "record_permutation_q025": float(record.quantile(0.025)),
            "record_permutation_q975": float(record.quantile(0.975)),
            "median_paired_difference": float(paired.median()),
            "empirical_p_participant_not_greater": float((1 + (paired <= 0).sum()) / (1 + len(paired))),
            "permutations": len(paired),
        })
    return pd.DataFrame(summary), distribution


def summarize_outcome_null() -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_parquet(PRIVATE / "phase3_outcome_null.parquet")
    rows = []
    for (dataset, task, permutation, model), group in frame.groupby(
        ["dataset", "task", "permutation", "model"], sort=True
    ):
        truth = group["y_true"].astype(float).to_numpy()
        prediction = group["y_pred"].astype(float).to_numpy()
        rows.append({
            "dataset": dataset, "task": task, "permutation": int(permutation),
            "model": model, "mae": float(np.abs(truth - prediction).mean()),
        })
    metrics = pd.DataFrame(rows)
    pivot = metrics.pivot(index=["dataset", "task", "permutation"], columns="model", values="mae").reset_index()
    pivot["ridge_improvement_over_mean"] = pivot["feature_free_mean"] - pivot["ridge"]
    summary = pivot.groupby(["dataset", "task"], sort=True)["ridge_improvement_over_mean"].agg(
        median="median", q025=lambda values: values.quantile(0.025), q975=lambda values: values.quantile(0.975),
        positive_share=lambda values: (values > 0).mean(), permutations="size",
    ).reset_index()
    return summary, pivot


def paper1_replication(performance: pd.DataFrame, config: dict) -> pd.DataFrame:
    expected_accuracy = {
        ("Suturing", "same_participant"): 0.9230769231,
        ("Knot Tying", "same_participant"): 0.9722222222,
        ("Needle Passing", "same_participant"): 0.9285714286,
        ("Suturing", "held_out_participant"): 0.4358974359,
        ("Knot Tying", "held_out_participant"): 0.3055555556,
        ("Needle Passing", "held_out_participant"): 0.3928571429,
    }
    expected_mae = {
        ("Suturing", "same_participant"): 3.2023,
        ("Knot Tying", "same_participant"): 2.8803,
        ("Needle Passing", "same_participant"): 3.79,
        ("Suturing", "held_out_participant"): 4.56,
        ("Knot Tying", "held_out_participant"): 3.56,
        ("Needle Passing", "held_out_participant"): 4.91,
    }
    rows = []
    for (task, protocol), expected in expected_accuracy.items():
        match = performance.loc[
            (performance["dataset"] == "JIGSAWS") & (performance["task"] == task)
            & (performance["protocol"] == protocol) & (performance["model"] == "multinomial_logistic")
        ]
        observed = float(match["accuracy"].iloc[0])
        tolerance = float(config["paper1_replication_tolerance"]["skill_accuracy_absolute"])
        rows.append({"endpoint": "skill_accuracy", "task": task, "protocol": protocol, "paper1": expected, "phase3": observed, "absolute_difference": abs(observed - expected), "tolerance": tolerance, "within_tolerance": abs(observed - expected) <= tolerance})
    for (task, protocol), expected in expected_mae.items():
        match = performance.loc[
            (performance["dataset"] == "JIGSAWS") & (performance["task"] == task)
            & (performance["protocol"] == protocol) & (performance["model"] == "ridge")
        ]
        observed = float(match["mae"].iloc[0])
        tolerance = float(config["paper1_replication_tolerance"]["grs_mae_points"])
        rows.append({"endpoint": "grs_mae", "task": task, "protocol": protocol, "paper1": expected, "phase3": observed, "absolute_difference": abs(observed - expected), "tolerance": tolerance, "within_tolerance": abs(observed - expected) <= tolerance})
    return pd.DataFrame(rows)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.12g", na_rep="NA", lineterminator="\n")


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    expected_config_hash = config_sha256(config)
    prediction_paths = sorted(PRIVATE.glob("phase3_*.parquet"))
    if len(prediction_paths) != 5:
        raise ValueError(f"expected five private prediction artifacts, found {prediction_paths}")
    analysis_commits: set[str] = set()
    for path in prediction_paths:
        frame = pd.read_parquet(path)
        assert set(frame["config_sha256"]) == {expected_config_hash}, path
        assert frame["trial_key"].notna().all(), path
        analysis_commits.update(frame["git_commit"].astype(str).unique())
    if len(analysis_commits) != 1:
        raise ValueError(f"prediction artifacts span multiple analysis commits: {analysis_commits}")
    analysis_commit = next(iter(analysis_commits))

    performance, gaps = summarize_performance(config)
    identity, identity_null = summarize_identity(config)
    skill_summary, skill_distribution = summarize_skill_permutations()
    outcome_summary, outcome_distribution = summarize_outcome_null()
    replication = paper1_replication(performance, config)
    outputs = {
        "phase3_performance.csv": performance,
        "phase3_protocol_gap.csv": gaps,
        "phase3_identity_probes.csv": identity,
        "phase3_identity_null_distribution.csv": identity_null,
        "phase3_skill_permutation_summary.csv": skill_summary,
        "phase3_skill_permutation_distribution.csv": skill_distribution,
        "phase3_outcome_null_summary.csv": outcome_summary,
        "phase3_outcome_null_distribution.csv": outcome_distribution,
        "phase3_paper1_replication.csv": replication,
    }
    METRICS.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        frame.insert(0, "analysis_commit", analysis_commit)
        frame.insert(1, "config_sha256", expected_config_hash)
        write_csv(METRICS / name, frame)

    artifacts = []
    for path in prediction_paths:
        artifacts.append({
            "artifact": f"private_{path.stem}", "path": str(path.relative_to(ROOT)),
            "kind": "private_oof_predictions",
            "rows": len(pd.read_parquet(path)), "sha256": sha256(path),
            "analysis_commit": analysis_commit, "config_sha256": expected_config_hash,
            "redistribution": "not committed; regenerate from authorized/public sources",
        })
    canary = METRICS / "phase3_leakage_canary.json"
    for path in [*(METRICS / name for name in outputs), canary]:
        artifacts.append({
            "artifact": f"aggregate_{path.stem}", "path": str(path.relative_to(ROOT)),
            "kind": "committed_aggregate",
            "rows": len(pd.read_csv(path)) if path.suffix == ".csv" else 1,
            "sha256": sha256(path), "analysis_commit": analysis_commit,
            "config_sha256": expected_config_hash, "redistribution": "committed",
        })
    manifest = ROOT / "data" / "manifests" / "phase3_artifacts.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(artifacts[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(artifacts)
    print(f"Wrote {len(outputs)} metric tables and {manifest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
