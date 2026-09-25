#!/usr/bin/env python3
"""Run I4 gradient-reversal encoders and lambda-zero capacity controls."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from surgical_skill2.adversarial import train_adversarial
from surgical_skill2.audit import config_sha256, inner_splits, stable_seed
from surgical_skill2.interventions import StandardizedFeatures, finite_columns
from scripts.run_phase4_linear import base_record, folded_features, fresh_probe


CONFIG_PATH = ROOT / "configs" / "experiments" / "phase4_interventions.yaml"
PRIVATE = ROOT / "results" / "predictions" / "private"


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def train_model(
    values: np.ndarray, target: np.ndarray, identity: np.ndarray,
    strength: float, seed: int, config: dict, epochs: int,
):
    settings = config["adversarial"]
    return train_adversarial(
        values, target, identity,
        identity_strength=strength, seed=seed,
        hidden=int(settings["hidden_width"]), latent=int(settings["latent_width"]),
        epochs=epochs, learning_rate=float(settings["learning_rate"]),
        weight_decay=float(settings["weight_decay"]),
    )


def choose_lambda(
    train: pd.DataFrame, target: np.ndarray, protocol: str,
    columns: list[str], config: dict, outer_label: str,
) -> tuple[float, dict[float, dict[str, float]]]:
    settings = config["adversarial"]
    splits = inner_splits(train, protocol)[: int(settings["selection_inner_splits"])]
    identity = train["participant_key"].astype(str).to_numpy()
    results: dict[float, dict[str, float]] = {}
    for strength in settings["lambda_grid"]:
        task_scores = []
        identity_scores = []
        for split_number, (fit_index, validation_index) in enumerate(splits):
            fit = train.iloc[fit_index]
            validation = train.iloc[validation_index]
            transformer = StandardizedFeatures(columns).fit(fit)
            fit_values = transformer.transform(fit)
            validation_values = transformer.transform(validation)
            model = train_model(
                fit_values, target[fit_index], identity[fit_index], float(strength),
                stable_seed(config["base_seed"], outer_label, strength, split_number, "selection"),
                config, int(settings["selection_epochs"]),
            )
            task_scores.append(mean_absolute_error(target[validation_index], model.predict(validation_values)))
            identity_scores.append(model.training_identity_accuracy(fit_values, identity[fit_index]))
        results[float(strength)] = {
            "task_mae": float(np.mean(task_scores)),
            "identity_head_training_accuracy": float(np.mean(identity_scores)),
        }
    baseline = results[0.0]["task_mae"]
    margin = float(settings["utility_margin_target_sd"]) * float(np.std(target))
    allowed = [strength for strength in results if results[strength]["task_mae"] <= baseline + margin]
    selected = min(allowed, key=lambda strength: (results[strength]["identity_head_training_accuracy"], strength))
    return float(selected), results


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config_hash = config_sha256(config)
    commit = git_commit()
    features = pd.read_csv(ROOT / "data" / "processed" / "private" / "phase2_features.csv", na_values=["NA"])
    task_records: list[dict] = []
    probe_records: list[dict] = []
    selection_records: list[dict] = []

    for protocol in config["protocols"]:
        folded = folded_features(features, protocol)
        eligible = folded.loc[folded["outcome_value"].notna()].copy()
        for (dataset, task), group in eligible.groupby(["dataset", "task"], sort=True):
            group = group.reset_index(drop=True)
            fold_values = group["test_fold"].astype(str).to_numpy()
            target = group["outcome_value"].to_numpy(dtype=float)
            for fold in sorted(set(fold_values)):
                train_mask = fold_values != fold
                test_mask = ~train_mask
                train = group.loc[train_mask].reset_index(drop=True)
                test = group.loc[test_mask].reset_index(drop=True)
                train_target = target[train_mask]
                test_target = target[test_mask]
                columns = finite_columns(train)
                label = f"{protocol}/{dataset}/{task}/{fold}"
                selected_lambda, selection = choose_lambda(train, train_target, protocol, columns, config, label)
                selection_records.append({
                    "dataset": dataset, "task": task, "protocol": protocol, "test_fold": fold,
                    "selected_lambda": selected_lambda, "selection_json": json.dumps(selection, sort_keys=True),
                    "git_commit": commit, "config_sha256": config_hash,
                })
                transformer = StandardizedFeatures(columns).fit(train)
                train_values = transformer.transform(train)
                test_values = transformer.transform(test)
                train_identity = train["participant_key"].astype(str).to_numpy()
                for seed in config["seeds"]:
                    # Reuse the exact initialization and minibatch order so the
                    # lambda-zero model is a strict capacity control for I4.
                    network_seed = stable_seed(seed, label, "capacity_matched_network")
                    conditions = [
                        ("I4_capacity_lambda0", 0.0, train_identity),
                        ("I4_adversarial", selected_lambda, train_identity),
                    ]
                    shuffled_identity = np.random.default_rng(
                        stable_seed(seed, label, "shuffled_identity")
                    ).permutation(train_identity)
                    conditions.append(("I4_shuffled_identity", selected_lambda, shuffled_identity))
                    for intervention, strength, training_identity in conditions:
                        model = train_model(
                            train_values, train_target, training_identity, strength,
                            network_seed, config,
                            int(config["adversarial"]["final_epochs"]),
                        )
                        prediction = model.predict(test_values)
                        train_representation = model.encode(train_values)
                        test_representation = model.encode(test_values)
                        for index, (_, row) in enumerate(test.iterrows()):
                            record = base_record(row, protocol, intervention, "adversarial_mlp", int(seed), config_hash, commit)
                            record.update({
                                "target_name": row["outcome_name"], "y_true": float(test_target[index]),
                                "y_pred": float(prediction[index]), "selected_lambda": selected_lambda,
                                "identity_strength": strength,
                            })
                            task_records.append(record)
                        if protocol == "same_participant":
                            for probe_name in ("linear_probe", "nonlinear_probe"):
                                probe_seed = stable_seed(seed, dataset, task, fold, intervention, probe_name)
                                probe_prediction, true_probability, selected = fresh_probe(
                                    train_representation, test_representation, train, test,
                                    probe_name, config, probe_seed,
                                )
                                truth = test["participant_key"].astype(str).to_numpy()
                                for index, (_, row) in enumerate(test.iterrows()):
                                    record = base_record(row, protocol, intervention, probe_name, int(seed), config_hash, commit)
                                    record.update({
                                        "target_name": "participant_identity", "y_true": truth[index],
                                        "y_pred": probe_prediction[index],
                                        "true_probability": float(true_probability[index]),
                                        "selected_hyperparameter": selected,
                                        "selected_lambda": selected_lambda, "identity_strength": strength,
                                    })
                                    probe_records.append(record)
                print(f"Adversarial {protocol} {dataset}/{task} {fold} lambda={selected_lambda:g}", flush=True)

    PRIVATE.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(task_records).to_parquet(PRIVATE / "phase4_adversarial_task.parquet", index=False, compression="zstd")
    probes = pd.DataFrame(probe_records)
    probes["y_true"] = probes["y_true"].map(str); probes["y_pred"] = probes["y_pred"].map(str)
    probes.to_parquet(PRIVATE / "phase4_adversarial_probes.parquet", index=False, compression="zstd")
    pd.DataFrame(selection_records).to_parquet(PRIVATE / "phase4_adversarial_selection.parquet", index=False, compression="zstd")
    print(f"Wrote {len(task_records)} task, {len(probe_records)} probe, and {len(selection_records)} selection rows")


if __name__ == "__main__":
    main()
