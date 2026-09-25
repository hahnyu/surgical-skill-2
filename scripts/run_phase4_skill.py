#!/usr/bin/env python3
"""Evaluate JIGSAWS same-participant skill classification after Phase 4 suppression."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.run_phase4_adversarial import train_model
from scripts.run_phase4_linear import base_record, folded_features, representation_frame
from surgical_skill2.audit import (
    aligned_probabilities,
    config_sha256,
    logistic_pipeline,
    probability_fields,
    select_logistic_c,
    stable_seed,
)
from surgical_skill2.interventions import (
    DurationResidualizer,
    IdentitySubspaceRemover,
    RandomSubspaceRemover,
    StandardizedFeatures,
    finite_columns,
)


CONFIG_PATH = ROOT / "configs" / "experiments" / "phase4_interventions.yaml"
PRIVATE = ROOT / "results" / "predictions" / "private"


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def classify_skill(
    train_values: np.ndarray,
    test_values: np.ndarray,
    train: pd.DataFrame,
    test: pd.DataFrame,
    config: dict,
) -> tuple[np.ndarray, np.ndarray, float]:
    train_skill = train["skill"].astype(str).to_numpy()
    test_skill = test["skill"].astype(str).to_numpy()
    classes = np.array(sorted(np.unique(train_skill)))
    frame, columns = representation_frame(train_values, train)
    c_value = select_logistic_c(
        frame, train_skill, columns, "same_participant",
        config["linear"]["probe_c_grid"], classes,
    )
    fitted = logistic_pipeline(c_value).fit(frame[columns], train_skill)
    probabilities = aligned_probabilities(
        fitted, pd.DataFrame(test_values, columns=columns), classes
    )
    prediction = classes[np.argmax(probabilities, axis=1)]
    _, true_probability = probability_fields(probabilities, classes, test_skill)
    return prediction, true_probability, float(c_value)


def append_predictions(
    records: list[dict], train_values: np.ndarray, test_values: np.ndarray,
    train: pd.DataFrame, test: pd.DataFrame, config: dict,
    intervention: str, seed: int, config_hash: str, commit: str,
    selected_k: int = 0, selected_lambda: float = 0.0,
) -> None:
    prediction, true_probability, c_value = classify_skill(
        train_values, test_values, train, test, config
    )
    truth = test["skill"].astype(str).to_numpy()
    for index, (_, row) in enumerate(test.iterrows()):
        record = base_record(
            row, "same_participant", intervention, "skill_logistic",
            int(seed), config_hash, commit,
        )
        record.update({
            "target_name": "self_declared_skill", "y_true": truth[index],
            "y_pred": prediction[index],
            "true_probability": float(true_probability[index]),
            "selected_hyperparameter": f"C={c_value:g}",
            "selected_k": int(selected_k),
            "selected_lambda": float(selected_lambda),
        })
        records.append(record)


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config_hash = config_sha256(config)
    commit = git_commit()
    features = pd.read_csv(
        ROOT / "data" / "processed" / "private" / "phase2_features.csv",
        na_values=["NA"],
    )
    folded = folded_features(features, "same_participant")
    jigsaws = folded.loc[folded["dataset"] == "JIGSAWS"].copy()
    jigsaws["skill"] = jigsaws["condition"].str.rsplit("_", n=1).str[-1]
    linear_selection = pd.read_parquet(PRIVATE / "phase4_linear_selection.parquet")
    adversarial_selection = pd.read_parquet(PRIVATE / "phase4_adversarial_selection.parquet")
    records: list[dict] = []

    for (dataset, task), group in jigsaws.groupby(["dataset", "task"], sort=True):
        group = group.reset_index(drop=True)
        fold_values = group["test_fold"].astype(str).to_numpy()
        outcome = group["outcome_value"].to_numpy(dtype=float)
        for fold in sorted(set(fold_values)):
            train_mask = fold_values != fold
            test_mask = ~train_mask
            train = group.loc[train_mask].reset_index(drop=True)
            test = group.loc[test_mask].reset_index(drop=True)
            columns = finite_columns(train)
            identity = train["participant_key"].astype(str).to_numpy()
            chosen_k = int(linear_selection.loc[
                (linear_selection["dataset"] == dataset)
                & (linear_selection["task"] == task)
                & (linear_selection["protocol"] == "same_participant")
                & (linear_selection["test_fold"].astype(str) == str(fold)),
                "selected_k",
            ].iloc[0])
            removed = set(config["linear"]["remove_as_direct_duration"])
            transformers = {
                "I0_unsuppressed": StandardizedFeatures(columns).fit(train),
                "I1_duration_removed": StandardizedFeatures(
                    [column for column in columns if column not in removed]
                ).fit(train),
                "I2_duration_residualized": DurationResidualizer(columns).fit(train),
                "I3_identity_subspace": IdentitySubspaceRemover(
                    columns, chosen_k
                ).fit(train, identity),
                "random_projection": RandomSubspaceRemover(
                    columns, chosen_k,
                    stable_seed(config["base_seed"], dataset, task, str(fold)),
                ).fit(train),
            }
            for intervention, transformer in transformers.items():
                append_predictions(
                    records, transformer.transform(train), transformer.transform(test),
                    train, test, config, intervention, int(config["base_seed"]),
                    config_hash, commit,
                    selected_k=chosen_k if intervention in {
                        "I3_identity_subspace", "random_projection"
                    } else 0,
                )

            selected_lambda = float(adversarial_selection.loc[
                (adversarial_selection["dataset"] == dataset)
                & (adversarial_selection["task"] == task)
                & (adversarial_selection["protocol"] == "same_participant")
                & (adversarial_selection["test_fold"].astype(str) == str(fold)),
                "selected_lambda",
            ].iloc[0])
            standardizer = StandardizedFeatures(columns).fit(train)
            train_values = standardizer.transform(train)
            test_values = standardizer.transform(test)
            label = f"same_participant/{dataset}/{task}/{fold}"
            for seed in config["seeds"]:
                network_seed = stable_seed(seed, label, "capacity_matched_network")
                shuffled = np.random.default_rng(
                    stable_seed(seed, label, "shuffled_identity")
                ).permutation(identity)
                conditions = [
                    ("I4_capacity_lambda0", 0.0, identity),
                    ("I4_adversarial", selected_lambda, identity),
                    ("I4_shuffled_identity", selected_lambda, shuffled),
                ]
                for intervention, strength, training_identity in conditions:
                    model = train_model(
                        train_values, outcome[train_mask], training_identity, strength,
                        network_seed, config, int(config["adversarial"]["final_epochs"]),
                    )
                    append_predictions(
                        records, model.encode(train_values), model.encode(test_values),
                        train, test, config, intervention, int(seed), config_hash, commit,
                        selected_lambda=selected_lambda,
                    )
            print(f"Skill {task} {fold} k={chosen_k} lambda={selected_lambda:g}", flush=True)

    output = pd.DataFrame(records)
    output["y_true"] = output["y_true"].map(str)
    output["y_pred"] = output["y_pred"].map(str)
    output.to_parquet(PRIVATE / "phase4_skill.parquet", index=False, compression="zstd")
    print(f"Wrote {len(output)} skill predictions")


if __name__ == "__main__":
    main()
