#!/usr/bin/env python3
"""Run Phase 3 baselines, identity probes, and falsification controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from surgical_skill2.audit import (
    HARMONIZED_FEATURE_COLUMNS,
    aligned_probabilities,
    assert_no_leakage_columns,
    available_features,
    config_sha256,
    forest_pipeline,
    logistic_pipeline,
    probability_fields,
    regression_pipeline,
    select_forest_leaf,
    select_logistic_c,
    select_ridge_alpha,
    stable_seed,
)


PRIVATE = ROOT / "results" / "predictions" / "private"
CONFIG_PATH = ROOT / "configs" / "experiments" / "phase3_baseline.yaml"


def load_config() -> tuple[dict, str]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return config, config_sha256(config)


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def with_folds(features: pd.DataFrame, protocol: str) -> pd.DataFrame:
    path = ROOT / "data" / "folds" / f"{protocol}.csv"
    folds = pd.read_csv(path)
    merged = features.merge(
        folds[["trial_key", "protocol", "test_fold"]], on="trial_key", how="left", validate="one_to_one"
    )
    if merged["test_fold"].isna().any() or set(merged["protocol"]) != {protocol}:
        raise ValueError(f"incomplete {protocol} fold join")
    return merged


def base_record(
    row: pd.Series, protocol: str, model: str, intervention: str, seed: int,
    target_name: str, config_hash: str, commit: str,
) -> dict:
    return {
        "dataset": row["dataset"], "version": row["version"], "task": row["task"],
        "participant_key": row["participant_key"], "trial_key": row["trial_key"],
        "session": row.get("session"), "test_fold": row["test_fold"], "protocol": protocol,
        "intervention": intervention, "model": model, "seed": seed,
        "target_name": target_name, "exclusion_flag": "included",
        "git_commit": commit, "config_sha256": config_hash,
    }


def regression_oof(
    frame: pd.DataFrame, protocol: str, model_name: str, target: np.ndarray,
    target_name: str, config: dict, config_hash: str, commit: str,
    *, fixed_alpha: float | None = None,
) -> list[dict]:
    seed = int(config["seed"])
    records: list[dict] = []
    for fold in sorted(frame["test_fold"].unique()):
        train = frame.loc[frame["test_fold"] != fold].reset_index(drop=True)
        test = frame.loc[frame["test_fold"] == fold].reset_index(drop=True)
        train_target = target[frame["test_fold"].to_numpy() != fold]
        test_target = target[frame["test_fold"].to_numpy() == fold]
        if model_name == "feature_free_mean":
            prediction = np.repeat(float(np.mean(train_target)), len(test))
            selected = "mean"
            intervention = "reference"
        elif model_name == "feature_free_median":
            prediction = np.repeat(float(np.median(train_target)), len(test))
            selected = "median"
            intervention = "reference"
        else:
            duration_only = model_name == "duration_ridge"
            columns = available_features(train, duration_only=duration_only)
            if fixed_alpha is None:
                alpha = select_ridge_alpha(
                    train, train_target, columns, protocol,
                    config["models"]["regression"]["alpha_grid"],
                )
            else:
                alpha = float(fixed_alpha)
            fitted = regression_pipeline(alpha).fit(train[columns], train_target)
            prediction = fitted.predict(test[columns])
            selected = f"alpha={alpha:g}"
            intervention = "baseline_duration_only" if duration_only else "I0_unsuppressed"
        for index, (_, row) in enumerate(test.iterrows()):
            record = base_record(row, protocol, model_name, intervention, seed, target_name, config_hash, commit)
            record.update({
                "y_true": float(test_target[index]), "y_pred": float(prediction[index]),
                "confidence": np.nan, "true_probability": np.nan,
                "selected_hyperparameter": selected,
            })
            records.append(record)
    return records


def _constant_probabilities(train_target: np.ndarray, classes: np.ndarray, count: int) -> np.ndarray:
    frequencies = pd.Series(train_target).value_counts(normalize=True)
    probabilities = np.array([float(frequencies.get(label, 0.0)) for label in classes])
    probabilities = np.maximum(probabilities, np.finfo(float).eps)
    probabilities /= probabilities.sum()
    return np.tile(probabilities, (count, 1))


def classification_oof(
    frame: pd.DataFrame, protocol: str, model_name: str, target: np.ndarray,
    target_name: str, config: dict, config_hash: str, commit: str,
    *, fixed_c: float | None = None, permutation: int | None = None,
    permutation_type: str | None = None,
) -> list[dict]:
    seed = int(config["seed"])
    classes = np.array(sorted(np.unique(target).astype(str)))
    records: list[dict] = []
    fold_values = frame["test_fold"].to_numpy()
    for fold in sorted(frame["test_fold"].unique()):
        train_mask = fold_values != fold
        test_mask = ~train_mask
        train = frame.loc[train_mask].reset_index(drop=True)
        test = frame.loc[test_mask].reset_index(drop=True)
        train_target = target[train_mask].astype(str)
        test_target = target[test_mask].astype(str)
        if model_name == "majority":
            probabilities = _constant_probabilities(train_target, classes, len(test))
            prediction = np.repeat(pd.Series(train_target).mode().sort_values().iloc[0], len(test))
            selected = "training_fold_mode"
            intervention = "reference"
        elif model_name == "empirical_chance":
            probabilities = _constant_probabilities(train_target, classes, len(test))
            rng = np.random.default_rng(stable_seed(seed, target_name, fold, permutation, "chance"))
            prediction = rng.choice(classes, size=len(test), p=probabilities[0])
            selected = "training_fold_class_prior"
            intervention = "reference"
        elif model_name == "identity_lookup":
            lookup = train.assign(_target=train_target).groupby("participant_key")["_target"].agg(
                lambda values: values.mode().sort_values().iloc[0]
            )
            prediction = test["participant_key"].map(lookup).astype(str).to_numpy()
            if (prediction == "nan").any():
                raise ValueError("identity lookup used with an unseen participant")
            probabilities = np.full((len(test), len(classes)), np.finfo(float).eps)
            for row_index, label in enumerate(prediction):
                probabilities[row_index, np.flatnonzero(classes == label)[0]] = 1.0
            probabilities /= probabilities.sum(axis=1, keepdims=True)
            selected = "training_fold_participant_mode"
            intervention = "positive_control"
        else:
            duration_only = model_name == "duration_logistic"
            columns = available_features(train, duration_only=duration_only)
            c_value = float(fixed_c) if fixed_c is not None else select_logistic_c(
                train, train_target, columns, protocol,
                config["models"]["skill_classification"]["c_grid"], classes,
            )
            fitted = logistic_pipeline(c_value).fit(train[columns], train_target)
            probabilities = aligned_probabilities(fitted, test[columns], classes)
            prediction = classes[np.argmax(probabilities, axis=1)]
            selected = f"C={c_value:g}"
            intervention = "baseline_duration_only" if duration_only else "I0_unsuppressed"
        confidence, true_probability = probability_fields(probabilities, classes, test_target)
        for index, (_, row) in enumerate(test.iterrows()):
            record = base_record(row, protocol, model_name, intervention, seed, target_name, config_hash, commit)
            record.update({
                "y_true": test_target[index], "y_pred": prediction[index],
                "confidence": float(confidence[index]), "true_probability": float(true_probability[index]),
                "selected_hyperparameter": selected,
                "permutation": permutation, "permutation_type": permutation_type,
            })
            records.append(record)
    return records


def identity_probe_oof(
    frame: pd.DataFrame, model_name: str, config: dict, config_hash: str, commit: str,
    *, target: np.ndarray | None = None, fixed_c: float | None = None,
    permutation: int | None = None,
) -> list[dict]:
    protocol = "same_participant"
    seed = int(config["seed"])
    target = frame["participant_key"].astype(str).to_numpy() if target is None else target.astype(str)
    classes = np.array(sorted(frame["participant_key"].astype(str).unique()))
    fold_values = frame["test_fold"].to_numpy()
    records: list[dict] = []
    for fold in sorted(frame["test_fold"].unique()):
        train_mask = fold_values != fold
        test_mask = ~train_mask
        train = frame.loc[train_mask].reset_index(drop=True)
        test = frame.loc[test_mask].reset_index(drop=True)
        train_target = target[train_mask]
        test_target = target[test_mask]
        if model_name in {"majority", "empirical_chance"}:
            probabilities = _constant_probabilities(train_target, classes, len(test))
            if model_name == "majority":
                prediction = np.repeat(pd.Series(train_target).mode().sort_values().iloc[0], len(test))
            else:
                rng = np.random.default_rng(stable_seed(seed, frame.iloc[0]["dataset"], frame.iloc[0]["task"], fold, permutation))
                prediction = rng.choice(classes, size=len(test), p=probabilities[0])
            selected = "training_fold_reference"
        else:
            duration_only = model_name == "duration_logistic"
            columns = available_features(train, duration_only=duration_only)
            if model_name == "random_forest":
                leaf = select_forest_leaf(
                    train, train_target, columns, protocol,
                    config["models"]["identity_probe"]["forest_min_samples_leaf"],
                    config["models"]["identity_probe"]["forest_trees"], seed,
                )
                fitted = forest_pipeline(
                    leaf, config["models"]["identity_probe"]["forest_trees"],
                    stable_seed(seed, frame.iloc[0]["dataset"], frame.iloc[0]["task"], fold),
                ).fit(train[columns], train_target)
                selected = f"min_samples_leaf={leaf}"
            else:
                c_value = float(fixed_c) if fixed_c is not None else select_logistic_c(
                    train, train_target, columns, protocol,
                    config["models"]["identity_probe"]["c_grid"], classes,
                )
                fitted = logistic_pipeline(c_value).fit(train[columns], train_target)
                selected = f"C={c_value:g}"
            probabilities = aligned_probabilities(fitted, test[columns], classes)
            prediction = classes[np.argmax(probabilities, axis=1)]
        confidence, true_probability = probability_fields(probabilities, classes, test_target)
        for index, (_, row) in enumerate(test.iterrows()):
            record = base_record(
                row, protocol, model_name, "I0_probe", seed, "participant_identity", config_hash, commit
            )
            record.update({
                "y_true": test_target[index], "y_pred": prediction[index],
                "confidence": float(confidence[index]), "true_probability": float(true_probability[index]),
                "selected_hyperparameter": selected, "permutation": permutation,
                "permutation_type": "record_wise" if permutation is not None else None,
            })
            records.append(record)
    return records


def write_parquet(name: str, records: list[dict]) -> Path:
    PRIVATE.mkdir(parents=True, exist_ok=True)
    path = PRIVATE / name
    frame = pd.DataFrame(records)
    # A shared artifact contains numeric task outcomes and categorical skill
    # labels. Persist both losslessly as strings; metric code selects by target
    # and converts continuous outcomes explicitly.
    frame["y_true"] = frame["y_true"].map(str)
    frame["y_pred"] = frame["y_pred"].map(str)
    frame.to_parquet(path, index=False, compression="zstd")
    print(f"Wrote {path.relative_to(ROOT)}: {len(frame)} rows", flush=True)
    return path


def run_core(features: pd.DataFrame, config: dict, config_hash: str, commit: str) -> None:
    performance: list[dict] = []
    for protocol in config["protocols"]:
        folded = with_folds(features, protocol)
        eligible = folded.loc[folded["outcome_value"].notna()].copy()
        for (dataset, task), group in eligible.groupby(["dataset", "task"], sort=True):
            group = group.reset_index(drop=True)
            target = group["outcome_value"].to_numpy(dtype=float)
            target_name = str(group["outcome_name"].iloc[0])
            for model in ("feature_free_mean", "feature_free_median", "duration_ridge", "ridge"):
                performance.extend(regression_oof(
                    group, protocol, model, target, target_name, config, config_hash, commit
                ))
            print(f"Core regression {protocol} {dataset}/{task}", flush=True)

        jigsaws = folded.loc[folded["dataset"] == "JIGSAWS"].copy()
        jigsaws["skill"] = jigsaws["condition"].str.rsplit("_", n=1).str[-1]
        for task, group in jigsaws.groupby("task", sort=True):
            group = group.reset_index(drop=True)
            target = group["skill"].astype(str).to_numpy()
            models = ["majority", "duration_logistic", "multinomial_logistic"]
            if protocol == "same_participant":
                models.append("identity_lookup")
            for model in models:
                performance.extend(classification_oof(
                    group, protocol, model, target, "self_declared_skill", config, config_hash, commit
                ))
            print(f"Core skill {protocol} {task}", flush=True)
    write_parquet("phase3_performance.parquet", performance)

    probes: list[dict] = []
    folded = with_folds(features, "same_participant")
    for (dataset, task), group in folded.groupby(["dataset", "task"], sort=True):
        group = group.reset_index(drop=True)
        for model in ("majority", "empirical_chance", "duration_logistic", "multinomial_logistic", "random_forest"):
            probes.extend(identity_probe_oof(group, model, config, config_hash, commit))
        print(f"Identity probes {dataset}/{task}", flush=True)
    write_parquet("phase3_identity_probes.parquet", probes)


def run_skill_permutations(features: pd.DataFrame, config: dict, config_hash: str, commit: str) -> None:
    folded = with_folds(features, "same_participant")
    jigsaws = folded.loc[folded["dataset"] == "JIGSAWS"].copy()
    jigsaws["skill"] = jigsaws["condition"].str.rsplit("_", n=1).str[-1]
    count = int(config["permutations"]["skill_participant_wise"])
    fixed_c = float(config["permutations"]["fixed_logistic_c"])
    records: list[dict] = []
    for task, group in jigsaws.groupby("task", sort=True):
        group = group.reset_index(drop=True)
        original = group["skill"].astype(str).to_numpy()
        records.extend(classification_oof(
            group, "same_participant", "permutation_logistic", original,
            "self_declared_skill", config, config_hash, commit,
            fixed_c=fixed_c, permutation=-1, permutation_type="observed",
        ))
        participant_labels = group.groupby("participant_key")["skill"].first().sort_index()
        for permutation in range(count):
            rng = np.random.default_rng(stable_seed(config["seed"], task, permutation, "skill"))
            shuffled_labels = rng.permutation(participant_labels.to_numpy())
            mapping = dict(zip(participant_labels.index, shuffled_labels, strict=True))
            participant_target = group["participant_key"].map(mapping).to_numpy(dtype=str)
            record_target = rng.permutation(original)
            records.extend(classification_oof(
                group, "same_participant", "permutation_logistic", participant_target,
                "self_declared_skill", config, config_hash, commit,
                fixed_c=fixed_c, permutation=permutation, permutation_type="participant_wise",
            ))
            records.extend(classification_oof(
                group, "same_participant", "permutation_logistic", record_target,
                "self_declared_skill", config, config_hash, commit,
                fixed_c=fixed_c, permutation=permutation, permutation_type="record_wise",
            ))
        print(f"Skill permutations {task}: {count} paired", flush=True)
    write_parquet("phase3_skill_permutations.parquet", records)


def run_negative_controls(features: pd.DataFrame, config: dict, config_hash: str, commit: str) -> None:
    identity_records: list[dict] = []
    folded_same = with_folds(features, "same_participant")
    identity_count = int(config["permutations"]["identity_record_wise"])
    fixed_c = float(config["permutations"]["fixed_logistic_c"])
    for (dataset, task), group in folded_same.groupby(["dataset", "task"], sort=True):
        group = group.reset_index(drop=True)
        truth = group["participant_key"].astype(str).to_numpy()
        for permutation in range(identity_count):
            rng = np.random.default_rng(stable_seed(config["seed"], dataset, task, permutation, "identity"))
            identity_records.extend(identity_probe_oof(
                group, "multinomial_logistic", config, config_hash, commit,
                target=rng.permutation(truth), fixed_c=fixed_c, permutation=permutation,
            ))
        print(f"Identity null {dataset}/{task}: {identity_count}", flush=True)
    write_parquet("phase3_identity_null.parquet", identity_records)

    outcome_records: list[dict] = []
    folded_held = with_folds(features, "held_out_participant")
    eligible = folded_held.loc[folded_held["outcome_value"].notna()].copy()
    outcome_count = int(config["permutations"]["continuous_outcome_record_wise"])
    fixed_alpha = float(config["permutations"]["fixed_ridge_alpha"])
    for (dataset, task), group in eligible.groupby(["dataset", "task"], sort=True):
        group = group.reset_index(drop=True)
        truth = group["outcome_value"].to_numpy(dtype=float)
        target_name = str(group["outcome_name"].iloc[0])
        for permutation in range(outcome_count):
            rng = np.random.default_rng(stable_seed(config["seed"], dataset, task, permutation, "outcome"))
            shuffled = rng.permutation(truth)
            for model in ("feature_free_mean", "ridge"):
                rows = regression_oof(
                    group, "held_out_participant", model, shuffled, target_name,
                    config, config_hash, commit, fixed_alpha=fixed_alpha,
                )
                for row in rows:
                    row["permutation"] = permutation
                    row["permutation_type"] = "record_wise"
                outcome_records.extend(rows)
        print(f"Outcome null {dataset}/{task}: {outcome_count}", flush=True)
    write_parquet("phase3_outcome_null.parquet", outcome_records)


def run_canary(features: pd.DataFrame, config: dict, config_hash: str, commit: str) -> None:
    detection = False
    try:
        assert_no_leakage_columns(HARMONIZED_FEATURE_COLUMNS + ["participant_code"])
    except ValueError:
        detection = True
    folded = with_folds(features, "same_participant")
    rows = []
    for (dataset, task), group in folded.groupby(["dataset", "task"], sort=True):
        correct = 0
        total = 0
        for fold in sorted(group["test_fold"].unique()):
            train = group.loc[group["test_fold"] != fold]
            test = group.loc[group["test_fold"] == fold]
            encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
            x_train = encoder.fit_transform(train[["participant_key"]])
            x_test = encoder.transform(test[["participant_key"]])
            model = LogisticRegression(C=1e6, max_iter=5000).fit(x_train, train["participant_key"])
            correct += int((model.predict(x_test) == test["participant_key"]).sum())
            total += len(test)
        rows.append({"dataset": dataset, "task": task, "one_hot_identity_accuracy": correct / total})
    payload = {
        "git_commit": commit, "config_sha256": config_hash,
        "forbidden_column_detected": detection,
        "canary_present_in_final_predictors": False,
        "positive_control": rows,
    }
    path = ROOT / "results" / "metrics" / "phase3_leakage_canary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["all", "core", "permutations", "negative-controls", "canary"], default="all")
    args = parser.parse_args()
    config, config_hash = load_config()
    commit = git_commit()
    features = pd.read_csv(ROOT / "data" / "processed" / "private" / "phase2_features.csv", na_values=["NA"])
    assert len(features) == 2501
    if args.part in {"all", "core"}:
        run_core(features, config, config_hash, commit)
    if args.part in {"all", "permutations"}:
        run_skill_permutations(features, config, config_hash, commit)
    if args.part in {"all", "negative-controls"}:
        run_negative_controls(features, config, config_hash, commit)
    if args.part in {"all", "canary"}:
        run_canary(features, config, config_hash, commit)


if __name__ == "__main__":
    main()
