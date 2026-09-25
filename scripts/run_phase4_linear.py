#!/usr/bin/env python3
"""Run I0–I3 summary-feature interventions and matched random controls."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from surgical_skill2.audit import (
    aligned_probabilities,
    config_sha256,
    forest_pipeline,
    logistic_pipeline,
    probability_fields,
    select_forest_leaf,
    select_logistic_c,
    stable_seed,
)
from surgical_skill2.interventions import (
    DurationResidualizer,
    IdentitySubspaceRemover,
    RandomSubspaceRemover,
    StandardizedFeatures,
    choose_identity_k,
    finite_columns,
)


CONFIG_PATH = ROOT / "configs" / "experiments" / "phase4_interventions.yaml"
PRIVATE = ROOT / "results" / "predictions" / "private"


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def folded_features(features: pd.DataFrame, protocol: str) -> pd.DataFrame:
    same = pd.read_csv(ROOT / "data" / "folds" / "same_participant.csv")[["trial_key", "test_fold"]].rename(columns={"test_fold": "identity_fold"})
    outer = pd.read_csv(ROOT / "data" / "folds" / f"{protocol}.csv")[["trial_key", "test_fold"]]
    result = features.merge(same, on="trial_key", validate="one_to_one").merge(outer, on="trial_key", validate="one_to_one")
    if len(result) != len(features):
        raise ValueError("incomplete fold join")
    return result


def representation_frame(values: np.ndarray, source: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    columns = [f"z{index:02d}" for index in range(values.shape[1])]
    frame = pd.DataFrame(values, columns=columns)
    frame["participant_key"] = source["participant_key"].astype(str).to_numpy()
    frame["test_fold"] = source["identity_fold"].astype(str).to_numpy()
    return frame, columns


def fresh_probe(
    train_values: np.ndarray,
    test_values: np.ndarray,
    train: pd.DataFrame,
    test: pd.DataFrame,
    model_name: str,
    config: dict,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, str]:
    train_identity = train["participant_key"].astype(str).to_numpy()
    test_identity = test["participant_key"].astype(str).to_numpy()
    classes = np.array(sorted(np.unique(train_identity)))
    frame, columns = representation_frame(train_values, train)
    if model_name == "linear_probe":
        c_value = select_logistic_c(
            frame, train_identity, columns, "same_participant",
            config["linear"]["probe_c_grid"], classes,
        )
        fitted = logistic_pipeline(c_value).fit(frame[columns], train_identity)
        test_frame = pd.DataFrame(test_values, columns=columns)
        probabilities = aligned_probabilities(fitted, test_frame, classes)
        selected = f"C={c_value:g}"
    else:
        leaf = select_forest_leaf(
            frame, train_identity, columns, "same_participant",
            config["linear"]["probe_forest_min_samples_leaf"],
            config["linear"]["probe_forest_trees"], seed,
        )
        fitted = forest_pipeline(leaf, config["linear"]["probe_forest_trees"], seed).fit(frame[columns], train_identity)
        test_frame = pd.DataFrame(test_values, columns=columns)
        probabilities = aligned_probabilities(fitted, test_frame, classes)
        selected = f"min_samples_leaf={leaf}"
    prediction = classes[np.argmax(probabilities, axis=1)]
    _, true_probability = probability_fields(probabilities, classes, test_identity)
    return prediction, true_probability, selected


def make_transformers(
    train: pd.DataFrame,
    target: np.ndarray | None,
    protocol: str,
    config: dict,
    seed: int,
    outer_fold: str,
) -> tuple[dict[str, object], int, dict[int, dict[str, float]]]:
    columns = finite_columns(train)
    removed = set(config["linear"]["remove_as_direct_duration"])
    without_duration = [column for column in columns if column not in removed]
    chosen_k, selection = choose_identity_k(
        train, target, protocol, config["linear"]["identity_k_grid"],
        config["linear"]["utility_margin_target_sd"], columns,
    )
    identity = train["participant_key"].astype(str).to_numpy()
    transformers = {
        "I0_unsuppressed": StandardizedFeatures(columns).fit(train),
        "I1_duration_removed": StandardizedFeatures(without_duration).fit(train),
        "I2_duration_residualized": DurationResidualizer(columns).fit(train),
        "I3_identity_subspace": IdentitySubspaceRemover(columns, chosen_k).fit(train, identity),
        "random_projection": RandomSubspaceRemover(
            columns, chosen_k,
            stable_seed(seed, train.iloc[0]["dataset"], train.iloc[0]["task"], outer_fold),
        ).fit(train),
    }
    return transformers, chosen_k, selection


def base_record(row: pd.Series, protocol: str, intervention: str, model: str, seed: int, config_hash: str, commit: str) -> dict:
    return {
        "dataset": row["dataset"], "version": row["version"], "task": row["task"],
        "participant_key": row["participant_key"], "trial_key": row["trial_key"],
        "test_fold": row["test_fold"], "protocol": protocol,
        "intervention": intervention, "model": model, "seed": seed,
        "git_commit": commit, "config_sha256": config_hash,
    }


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config_hash = config_sha256(config)
    commit = git_commit()
    seed = int(config["base_seed"])
    features = pd.read_csv(ROOT / "data" / "processed" / "private" / "phase2_features.csv", na_values=["NA"])
    task_records: list[dict] = []
    probe_records: list[dict] = []
    selection_records: list[dict] = []

    for protocol in config["protocols"]:
        folded = folded_features(features, protocol)
        groups = folded.groupby(["dataset", "task"], sort=True)
        for (dataset, task), group in groups:
            group = group.reset_index(drop=True)
            has_target = group["outcome_value"].notna().all()
            if protocol == "held_out_participant" and not has_target:
                continue
            fold_values = group["test_fold"].astype(str).to_numpy()
            full_target = group["outcome_value"].to_numpy(dtype=float) if has_target else None
            for fold in sorted(set(fold_values)):
                train_mask = fold_values != fold
                test_mask = ~train_mask
                train = group.loc[train_mask].reset_index(drop=True)
                test = group.loc[test_mask].reset_index(drop=True)
                train_target = full_target[train_mask] if has_target else None
                test_target = full_target[test_mask] if has_target else None
                transformers, chosen_k, selection = make_transformers(
                    train, train_target, protocol, config, seed, str(fold)
                )
                selection_records.append({
                    "dataset": dataset, "task": task, "protocol": protocol, "test_fold": fold,
                    "selected_k": chosen_k, "selection_json": json.dumps(selection, sort_keys=True),
                    "seed": seed, "git_commit": commit, "config_sha256": config_hash,
                })
                for intervention, transformer in transformers.items():
                    train_values = transformer.transform(train)
                    test_values = transformer.transform(test)
                    if has_target:
                        model = Ridge(alpha=float(config["linear"]["ridge_alpha"]))
                        model.fit(train_values, train_target)
                        prediction = model.predict(test_values)
                        for index, (_, row) in enumerate(test.iterrows()):
                            record = base_record(row, protocol, intervention, "ridge", seed, config_hash, commit)
                            record.update({
                                "target_name": row["outcome_name"], "y_true": float(test_target[index]),
                                "y_pred": float(prediction[index]), "selected_k": chosen_k if intervention in {"I3_identity_subspace", "random_projection"} else 0,
                            })
                            task_records.append(record)
                    if protocol == "same_participant":
                        for probe_name in ("linear_probe", "nonlinear_probe"):
                            probe_seed = stable_seed(seed, dataset, task, fold, intervention, probe_name)
                            prediction, true_probability, selected = fresh_probe(
                                train_values, test_values, train, test, probe_name, config, probe_seed
                            )
                            truth = test["participant_key"].astype(str).to_numpy()
                            for index, (_, row) in enumerate(test.iterrows()):
                                record = base_record(row, protocol, intervention, probe_name, seed, config_hash, commit)
                                record.update({
                                    "target_name": "participant_identity", "y_true": truth[index],
                                    "y_pred": prediction[index], "true_probability": float(true_probability[index]),
                                    "selected_hyperparameter": selected,
                                    "selected_k": chosen_k if intervention in {"I3_identity_subspace", "random_projection"} else 0,
                                })
                                probe_records.append(record)
                print(f"Linear interventions {protocol} {dataset}/{task} {fold}", flush=True)

    PRIVATE.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(task_records).to_parquet(PRIVATE / "phase4_linear_task.parquet", index=False, compression="zstd")
    probes = pd.DataFrame(probe_records)
    probes["y_true"] = probes["y_true"].map(str); probes["y_pred"] = probes["y_pred"].map(str)
    probes.to_parquet(PRIVATE / "phase4_linear_probes.parquet", index=False, compression="zstd")
    pd.DataFrame(selection_records).to_parquet(PRIVATE / "phase4_linear_selection.parquet", index=False, compression="zstd")
    print(f"Wrote {len(task_records)} task, {len(probe_records)} probe, and {len(selection_records)} selection rows")


if __name__ == "__main__":
    main()
