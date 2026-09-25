#!/usr/bin/env python3
"""Derive Phase 4 intervention aggregates from saved out-of-fold predictions."""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from surgical_skill2.audit import classification_metrics, config_sha256, stable_seed


PRIVATE = ROOT / "results" / "predictions" / "private"
METRICS = ROOT / "results" / "metrics"
CONFIG_PATH = ROOT / "configs" / "experiments" / "phase4_interventions.yaml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def interval(values: np.ndarray, replicates: int, seed: int) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(replicates, len(values)))
    return tuple(np.quantile(values[indices].mean(axis=1), [0.025, 0.975]))


def participant_values(frame: pd.DataFrame, values: np.ndarray) -> np.ndarray:
    work = frame[["participant_key"]].copy()
    work["value"] = values
    return work.groupby("participant_key", sort=True)["value"].mean().to_numpy()


def task_performance(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    keys = ["dataset", "task", "protocol", "target_name", "intervention", "model", "seed"]
    replicates = int(config["uncertainty"]["participant_bootstrap_replicates"])
    for key, group in frame.groupby(keys, sort=True):
        truth = group["y_true"].astype(float).to_numpy()
        prediction = group["y_pred"].astype(float).to_numpy()
        absolute_error = np.abs(truth - prediction)
        values = participant_values(group, absolute_error)
        low, high = interval(values, replicates, stable_seed(config["base_seed"], *key, "task"))
        rows.append({
            **dict(zip(keys, key, strict=True)), "trials": len(group),
            "participants": group["participant_key"].nunique(),
            "mae": float(absolute_error.mean()),
            "participant_average_mae": float(values.mean()),
            "ci_low": low, "ci_high": high,
        })
    return pd.DataFrame(rows)


def probe_performance(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["dataset", "task", "intervention", "model", "seed"]
    for key, group in frame.groupby(keys, sort=True):
        metrics = classification_metrics(group)
        correctness = (
            group["y_true"].astype(str) == group["y_pred"].astype(str)
        ).to_numpy(dtype=float)
        per_participant = participant_values(group, correctness)
        rows.append({
            **dict(zip(keys, key, strict=True)), "trials": len(group),
            "participants": group["participant_key"].nunique(), **metrics,
            "participant_average_accuracy": float(per_participant.mean()),
            "empirical_chance": 1.0 / group["participant_key"].nunique(),
        })
    return pd.DataFrame(rows)


def paired_task_effects(
    frame: pd.DataFrame, comparisons: list[tuple[str, str]], config: dict,
) -> pd.DataFrame:
    rows = []
    replicates = int(config["uncertainty"]["participant_bootstrap_replicates"])
    keys = ["dataset", "task", "protocol", "target_name", "seed"]
    join = keys + ["participant_key", "trial_key"]
    for candidate, baseline in comparisons:
        selected = frame.loc[frame["intervention"].isin([candidate, baseline])]
        wide = selected.pivot(index=join, columns="intervention", values="y_pred").reset_index()
        truth = selected.loc[selected["intervention"] == candidate, join + ["y_true"]]
        wide = wide.merge(truth, on=join, validate="one_to_one")
        for key, group in wide.groupby(keys, sort=True):
            y = group["y_true"].astype(float).to_numpy()
            difference = np.abs(y - group[candidate].astype(float)) - np.abs(y - group[baseline].astype(float))
            values = participant_values(group, difference)
            low, high = interval(
                values, replicates,
                stable_seed(config["base_seed"], candidate, baseline, *key, "task_effect"),
            )
            rows.append({
                **dict(zip(keys, key, strict=True)), "candidate": candidate,
                "baseline": baseline, "metric": "participant_average_mae_difference",
                "estimate": float(values.mean()), "ci_low": low, "ci_high": high,
                "participants": group["participant_key"].nunique(), "trials": len(group),
                "direction": "negative_favors_candidate",
            })
    return pd.DataFrame(rows)


def paired_classification_effects(
    frame: pd.DataFrame, comparisons: list[tuple[str, str]], config: dict,
    metric: str,
) -> pd.DataFrame:
    rows = []
    replicates = int(config["uncertainty"]["participant_bootstrap_replicates"])
    base_keys = ["dataset", "task", "seed"]
    if "model" in frame:
        base_keys.insert(2, "model")
    join = base_keys + ["participant_key", "trial_key"]
    for candidate, baseline in comparisons:
        selected = frame.loc[frame["intervention"].isin([candidate, baseline])]
        wide = selected.pivot(index=join, columns="intervention", values="y_pred").reset_index()
        truth = selected.loc[selected["intervention"] == candidate, join + ["y_true"]]
        wide = wide.merge(truth, on=join, validate="one_to_one")
        for key, group in wide.groupby(base_keys, sort=True):
            truth_values = group["y_true"].astype(str)
            candidate_correct = (group[candidate].astype(str) == truth_values).to_numpy(dtype=float)
            baseline_correct = (group[baseline].astype(str) == truth_values).to_numpy(dtype=float)
            values = participant_values(group, candidate_correct - baseline_correct)
            low, high = interval(
                values, replicates,
                stable_seed(config["base_seed"], candidate, baseline, *key, metric),
            )
            rows.append({
                **dict(zip(base_keys, key, strict=True)), "candidate": candidate,
                "baseline": baseline, "metric": metric,
                "estimate": float(values.mean()), "ci_low": low, "ci_high": high,
                "participants": group["participant_key"].nunique(), "trials": len(group),
            })
    return pd.DataFrame(rows)


def aggregate_probe_effect(
    frame: pd.DataFrame, candidate: str, baseline: str, config: dict,
) -> list[dict]:
    replicates = int(config["uncertainty"]["participant_bootstrap_replicates"])
    output = []
    for model, source in frame.groupby("model", sort=True):
        keys = ["dataset", "task", "seed", "participant_key", "trial_key"]
        selected = source.loc[source["intervention"].isin([candidate, baseline])]
        wide = selected.pivot(index=keys, columns="intervention", values="y_pred").reset_index()
        truth = selected.loc[selected["intervention"] == candidate, keys + ["y_true"]]
        wide = wide.merge(truth, on=keys, validate="one_to_one")
        arrays = []
        for _, group in wide.groupby(["dataset", "task", "seed"], sort=True):
            truth_values = group["y_true"].astype(str)
            difference = (
                (group[candidate].astype(str) == truth_values).to_numpy(dtype=float)
                - (group[baseline].astype(str) == truth_values).to_numpy(dtype=float)
            )
            arrays.append(participant_values(group, difference))
        point = float(np.mean([values.mean() for values in arrays]))
        rng = np.random.default_rng(stable_seed(config["base_seed"], candidate, baseline, model, "aggregate"))
        boot = np.column_stack([
            values[rng.integers(0, len(values), size=(replicates, len(values)))].mean(axis=1)
            for values in arrays
        ]).mean(axis=1)
        low, high = np.quantile(boot, [0.025, 0.975])
        output.append({
            "candidate": candidate, "baseline": baseline, "probe_model": model,
            "balanced_accuracy_difference": point, "ci_low": float(low),
            "ci_high": float(high), "groups": len(arrays),
            "probe_endpoint_passed": bool(high < 0),
        })
    return output


def skill_performance(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["dataset", "task", "intervention", "model", "seed"]
    for key, group in frame.groupby(keys, sort=True):
        metrics = classification_metrics(group)
        correctness = (
            group["y_true"].astype(str) == group["y_pred"].astype(str)
        ).to_numpy(dtype=float)
        rows.append({
            **dict(zip(keys, key, strict=True)), "trials": len(group),
            "participants": group["participant_key"].nunique(), **metrics,
            "participant_average_accuracy": float(participant_values(group, correctness).mean()),
        })
    return pd.DataFrame(rows)


def selection_summary(linear: pd.DataFrame, adversarial: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for parameter, frame, column in [
        ("k", linear, "selected_k"), ("lambda", adversarial, "selected_lambda")
    ]:
        groups = ["dataset", "task", "protocol", column]
        counts = frame.groupby(groups, sort=True).size().rename("folds").reset_index()
        totals = frame.groupby(["dataset", "task", "protocol"]).size().rename("total_folds").reset_index()
        counts = counts.merge(totals, on=["dataset", "task", "protocol"])
        for _, row in counts.iterrows():
            rows.append({
                "dataset": row["dataset"], "task": row["task"], "protocol": row["protocol"],
                "parameter": parameter, "value": float(row[column]), "folds": int(row["folds"]),
                "share": float(row["folds"] / row["total_folds"]),
            })
    return pd.DataFrame(rows)


def seed_stability(task: pd.DataFrame, identity: pd.DataFrame, skill: pd.DataFrame) -> pd.DataFrame:
    rows = []
    neural_task = task.loc[task["model"] == "adversarial_mlp"]
    for key, group in neural_task.groupby(["dataset", "task", "protocol", "intervention"], sort=True):
        values = group.groupby("seed")["participant_average_mae"].first().to_numpy()
        rows.append({
            "endpoint": "task_participant_average_mae", **dict(zip(["dataset", "task", "protocol", "intervention"], key, strict=True)),
            "model": "adversarial_mlp", "seed_mean": values.mean(), "seed_sd": values.std(ddof=1),
            "seed_min": values.min(), "seed_max": values.max(), "seed_range": values.max() - values.min(),
        })
    neural_identity = identity.loc[identity["intervention"].str.startswith("I4_")]
    for key, group in neural_identity.groupby(["dataset", "task", "intervention", "model"], sort=True):
        values = group.sort_values("seed")["balanced_accuracy"].to_numpy()
        rows.append({
            "endpoint": "identity_balanced_accuracy", "dataset": key[0], "task": key[1],
            "protocol": "same_participant", "intervention": key[2], "model": key[3],
            "seed_mean": values.mean(), "seed_sd": values.std(ddof=1),
            "seed_min": values.min(), "seed_max": values.max(), "seed_range": values.max() - values.min(),
        })
    neural_skill = skill.loc[skill["intervention"].str.startswith("I4_")]
    for key, group in neural_skill.groupby(["dataset", "task", "intervention", "model"], sort=True):
        values = group.sort_values("seed")["accuracy"].to_numpy()
        rows.append({
            "endpoint": "skill_accuracy", "dataset": key[0], "task": key[1],
            "protocol": "same_participant", "intervention": key[2], "model": key[3],
            "seed_mean": values.mean(), "seed_sd": values.std(ddof=1),
            "seed_min": values.min(), "seed_max": values.max(), "seed_range": values.max() - values.min(),
        })
    return pd.DataFrame(rows)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.12g", na_rep="NA", lineterminator="\n")


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config_hash = config_sha256(config)
    prediction_paths = sorted(PRIVATE.glob("phase4_*.parquet"))
    expected_names = {
        "phase4_linear_task.parquet", "phase4_linear_probes.parquet", "phase4_linear_selection.parquet",
        "phase4_adversarial_task.parquet", "phase4_adversarial_probes.parquet",
        "phase4_adversarial_selection.parquet", "phase4_skill.parquet",
    }
    if {path.name for path in prediction_paths} != expected_names:
        raise ValueError(f"unexpected Phase 4 prediction artifacts: {prediction_paths}")
    commits = set()
    for path in prediction_paths:
        frame = pd.read_parquet(path)
        if set(frame["config_sha256"]) != {config_hash}:
            raise ValueError(f"configuration mismatch: {path}")
        commits.update(frame["git_commit"].astype(str).unique())
    commit_text = ";".join(sorted(commits))

    linear_task = pd.read_parquet(PRIVATE / "phase4_linear_task.parquet")
    adversarial_task = pd.read_parquet(PRIVATE / "phase4_adversarial_task.parquet")
    linear_probes = pd.read_parquet(PRIVATE / "phase4_linear_probes.parquet")
    adversarial_probes = pd.read_parquet(PRIVATE / "phase4_adversarial_probes.parquet")
    skill = pd.read_parquet(PRIVATE / "phase4_skill.parquet")
    all_task = pd.concat([linear_task, adversarial_task], ignore_index=True)
    all_probes = pd.concat([linear_probes, adversarial_probes], ignore_index=True)

    task_metrics = task_performance(all_task, config)
    identity_metrics = probe_performance(all_probes)
    skill_metrics = skill_performance(skill)
    linear_comparisons = [
        ("I1_duration_removed", "I0_unsuppressed"),
        ("I2_duration_residualized", "I0_unsuppressed"),
        ("I3_identity_subspace", "I0_unsuppressed"),
        ("random_projection", "I0_unsuppressed"),
        ("random_projection", "I3_identity_subspace"),
    ]
    adversarial_comparisons = [
        ("I4_adversarial", "I4_capacity_lambda0"),
        ("I4_shuffled_identity", "I4_capacity_lambda0"),
    ]
    task_effects = pd.concat([
        paired_task_effects(linear_task, linear_comparisons, config),
        paired_task_effects(adversarial_task, adversarial_comparisons, config),
    ], ignore_index=True)
    identity_effects = pd.concat([
        paired_classification_effects(
            linear_probes, linear_comparisons, config,
            "participant_average_balanced_accuracy_difference",
        ),
        paired_classification_effects(
            adversarial_probes, adversarial_comparisons, config,
            "participant_average_balanced_accuracy_difference",
        ),
    ], ignore_index=True)
    skill_effects = pd.concat([
        paired_classification_effects(skill, linear_comparisons, config, "skill_accuracy_difference"),
        paired_classification_effects(skill, adversarial_comparisons, config, "skill_accuracy_difference"),
    ], ignore_index=True)

    verification = aggregate_probe_effect(
        adversarial_probes, "I4_adversarial", "I4_capacity_lambda0", config
    ) + aggregate_probe_effect(
        linear_probes, "I3_identity_subspace", "I0_unsuppressed", config
    )
    primary = pd.DataFrame(verification)
    candidate_pass = primary.groupby("candidate")["probe_endpoint_passed"].all().to_dict()
    chosen = "I4_adversarial" if candidate_pass.get("I4_adversarial", False) else "I3_identity_subspace"
    primary["candidate_verified"] = primary["candidate"].map(candidate_pass)
    primary["designated_primary"] = primary["candidate"] == chosen
    primary["decision_rule"] = (
        "I4 only if both fresh-probe participant-bootstrap upper bounds are below zero; otherwise I3"
    )

    linear_selection = pd.read_parquet(PRIVATE / "phase4_linear_selection.parquet")
    adversarial_selection = pd.read_parquet(PRIVATE / "phase4_adversarial_selection.parquet")
    selection = selection_summary(linear_selection, adversarial_selection)
    stability = seed_stability(task_metrics, identity_metrics, skill_metrics)

    ablations = []
    for candidate, baseline in linear_comparisons + adversarial_comparisons:
        identity_match = identity_effects.loc[
            (identity_effects["candidate"] == candidate) & (identity_effects["baseline"] == baseline)
        ]
        held_match = task_effects.loc[
            (task_effects["candidate"] == candidate) & (task_effects["baseline"] == baseline)
            & (task_effects["protocol"] == "held_out_participant")
        ]
        skill_match = skill_effects.loc[
            (skill_effects["candidate"] == candidate) & (skill_effects["baseline"] == baseline)
        ]
        probe_means = identity_match.groupby("model")["estimate"].mean().to_dict()
        ablations.append({
            "candidate": candidate, "baseline": baseline,
            "linear_probe_mean_difference": probe_means.get("linear_probe", np.nan),
            "nonlinear_probe_mean_difference": probe_means.get("nonlinear_probe", np.nan),
            "held_task_groups_improved": int((held_match["estimate"] < 0).sum()),
            "held_task_groups_harmed": int((held_match["estimate"] > 0).sum()),
            "held_task_groups_total": len(held_match),
            "mean_jigsaws_skill_accuracy_difference": float(skill_match["estimate"].mean()),
            "control_role": {
                "random_projection": "matched_dimension_control",
                "I4_shuffled_identity": "shuffled_identity_head_control",
                "I4_adversarial": "gradient_reversal_intervention",
            }.get(candidate, "intervention"),
        })
    ablation_log = pd.DataFrame(ablations)

    outputs = {
        "phase4_task_performance.csv": task_metrics,
        "phase4_identity_probes.csv": identity_metrics,
        "phase4_identity_effects.csv": identity_effects,
        "phase4_task_effects.csv": task_effects,
        "phase4_skill_performance.csv": skill_metrics,
        "phase4_skill_effects.csv": skill_effects,
        "phase4_primary_comparison.csv": primary,
        "phase4_selection.csv": selection,
        "phase4_seed_stability.csv": stability,
        "phase4_ablation_log.csv": ablation_log,
    }
    METRICS.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        frame.insert(0, "analysis_commits", commit_text)
        frame.insert(1, "config_sha256", config_hash)
        write_csv(METRICS / name, frame)

    artifacts = []
    for path in prediction_paths:
        frame = pd.read_parquet(path)
        artifacts.append({
            "artifact": f"private_{path.stem}", "path": str(path.relative_to(ROOT)),
            "kind": "private_oof_predictions", "rows": len(frame), "sha256": sha256(path),
            "analysis_commits": ";".join(sorted(frame["git_commit"].astype(str).unique())),
            "config_sha256": config_hash,
            "redistribution": "not committed; regenerate from authorized/public sources",
        })
    for name in outputs:
        path = METRICS / name
        artifacts.append({
            "artifact": f"aggregate_{path.stem}", "path": str(path.relative_to(ROOT)),
            "kind": "committed_aggregate", "rows": len(pd.read_csv(path)),
            "sha256": sha256(path), "analysis_commits": commit_text,
            "config_sha256": config_hash, "redistribution": "committed",
        })
    manifest = ROOT / "data" / "manifests" / "phase4_artifacts.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(artifacts[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(artifacts)
    print(f"Wrote {len(outputs)} Phase 4 metric tables; primary={chosen}")


if __name__ == "__main__":
    main()
