"""Fold-safe models and metrics for the Phase 3 baseline audit."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, f1_score, log_loss, mean_absolute_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


HARMONIZED_FEATURE_COLUMNS = [
    "duration_s", "psm1_samples", "psm2_samples", "psm1_sampling_hz", "psm2_sampling_hz",
    "bimanual_speed_correlation", "path_length_asymmetry",
    "psm1_path_length_m", "psm1_speed_mean_m_s", "psm1_speed_std_m_s",
    "psm1_speed_q10_m_s", "psm1_speed_q50_m_s", "psm1_speed_q90_m_s",
    "psm1_accel_abs_mean_m_s2", "psm1_accel_abs_q90_m_s2",
    "psm1_jerk_abs_mean_m_s3", "psm1_jerk_abs_q90_m_s3", "psm1_idle_fraction",
    "psm1_workspace_bbox_m3", "psm1_gap_fraction", "psm1_gripper_mean",
    "psm1_gripper_std", "psm1_gripper_range", "psm1_gripper_total_variation",
    "psm2_path_length_m", "psm2_speed_mean_m_s", "psm2_speed_std_m_s",
    "psm2_speed_q10_m_s", "psm2_speed_q50_m_s", "psm2_speed_q90_m_s",
    "psm2_accel_abs_mean_m_s2", "psm2_accel_abs_q90_m_s2",
    "psm2_jerk_abs_mean_m_s3", "psm2_jerk_abs_q90_m_s3", "psm2_idle_fraction",
    "psm2_workspace_bbox_m3", "psm2_gap_fraction", "psm2_gripper_mean",
    "psm2_gripper_std", "psm2_gripper_range", "psm2_gripper_total_variation",
]

FORBIDDEN_PREDICTOR_TOKENS = (
    "participant", "subject", "surgeon", "user", "trial", "filename", "source",
    "outcome", "target", "label", "condition", "session", "repetition", "dataset", "task",
)


def stable_seed(*parts: object) -> int:
    payload = "\0".join(str(part) for part in parts).encode()
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def assert_no_leakage_columns(columns: Iterable[str]) -> None:
    bad = [name for name in columns if any(token in name.lower() for token in FORBIDDEN_PREDICTOR_TOKENS)]
    if bad:
        raise ValueError(f"forbidden identifier/target columns in predictors: {bad}")


def available_features(train: pd.DataFrame, duration_only: bool = False) -> list[str]:
    requested = ["duration_s"] if duration_only else HARMONIZED_FEATURE_COLUMNS
    missing = [column for column in requested if column not in train]
    if missing:
        raise ValueError(f"missing harmonized feature columns: {missing}")
    assert_no_leakage_columns(requested)
    available = [column for column in requested if np.isfinite(pd.to_numeric(train[column], errors="coerce")).any()]
    if not available:
        raise ValueError("training fold has no finite predictor")
    return available


def regression_pipeline(alpha: float) -> Pipeline:
    regressor = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("ridge", Ridge(alpha=float(alpha))),
    ])
    return Pipeline([
        ("model", TransformedTargetRegressor(regressor=regressor, transformer=StandardScaler())),
    ])


def logistic_pipeline(c_value: float) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(C=float(c_value), solver="lbfgs", max_iter=5000)),
    ])


def forest_pipeline(min_samples_leaf: int, trees: int, seed: int) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("forest", RandomForestClassifier(
            n_estimators=int(trees), min_samples_leaf=int(min_samples_leaf),
            max_features="sqrt", class_weight="balanced_subsample",
            random_state=int(seed), n_jobs=-1,
        )),
    ])


def inner_splits(frame: pd.DataFrame, protocol: str) -> list[tuple[np.ndarray, np.ndarray]]:
    if protocol == "same_participant":
        result = []
        fold_values = frame["test_fold"].astype(str).to_numpy()
        unique_folds = sorted(set(fold_values))
        # Keep nested tuning modest when a dataset has many source repetitions
        # (PatCut has 24) while preserving repetition groups as indivisible.
        buckets = [unique_folds[index::5] for index in range(min(5, len(unique_folds)))]
        for bucket in buckets:
            validation_mask = np.isin(fold_values, bucket)
            validation = np.flatnonzero(validation_mask)
            training = np.flatnonzero(~validation_mask)
            if len(training) and len(validation):
                result.append((training, validation))
        return result
    if protocol == "held_out_participant":
        groups = frame["participant_key"].astype(str).to_numpy()
        unique = np.unique(groups)
        if len(unique) < 2:
            raise ValueError("held-out inner validation requires at least two participants")
        splitter = GroupKFold(n_splits=min(5, len(unique)))
        dummy = np.zeros(len(frame))
        return list(splitter.split(dummy, groups=groups))
    raise ValueError(f"unknown protocol: {protocol}")


def select_ridge_alpha(
    train: pd.DataFrame, target: np.ndarray, columns: list[str], protocol: str,
    alphas: Iterable[float],
) -> float:
    scores: dict[float, list[float]] = {float(alpha): [] for alpha in alphas}
    x = train[columns]
    for fit_index, validation_index in inner_splits(train, protocol):
        for alpha in scores:
            model = regression_pipeline(alpha)
            model.fit(x.iloc[fit_index], target[fit_index])
            prediction = model.predict(x.iloc[validation_index])
            scores[alpha].append(mean_absolute_error(target[validation_index], prediction))
    return min(scores, key=lambda value: (float(np.mean(scores[value])), value))


def aligned_probabilities(model: Pipeline, values: pd.DataFrame, classes: np.ndarray) -> np.ndarray:
    raw = model.predict_proba(values)
    model_classes = np.asarray(model.classes_).astype(str)
    output = np.full((len(values), len(classes)), np.finfo(float).eps)
    for source, label in enumerate(model_classes):
        matches = np.flatnonzero(classes == label)
        if len(matches):
            output[:, matches[0]] = raw[:, source]
    output /= output.sum(axis=1, keepdims=True)
    return output


def select_logistic_c(
    train: pd.DataFrame, target: np.ndarray, columns: list[str], protocol: str,
    c_grid: Iterable[float], classes: np.ndarray,
) -> float:
    scores: dict[float, list[float]] = {float(value): [] for value in c_grid}
    x = train[columns]
    for fit_index, validation_index in inner_splits(train, protocol):
        if len(np.unique(target[fit_index])) < 2:
            continue
        for c_value in scores:
            model = logistic_pipeline(c_value)
            model.fit(x.iloc[fit_index], target[fit_index])
            probabilities = aligned_probabilities(model, x.iloc[validation_index], classes)
            scores[c_value].append(log_loss(target[validation_index], probabilities, labels=classes))
    populated = {key: value for key, value in scores.items() if value}
    if not populated:
        raise ValueError("no valid inner classification split")
    return min(populated, key=lambda value: (float(np.mean(populated[value])), value))


def select_forest_leaf(
    train: pd.DataFrame, target: np.ndarray, columns: list[str], protocol: str,
    leaf_grid: Iterable[int], trees: int, seed: int,
) -> int:
    scores: dict[int, list[float]] = {int(value): [] for value in leaf_grid}
    x = train[columns]
    for split_number, (fit_index, validation_index) in enumerate(inner_splits(train, protocol)):
        for leaf in scores:
            model = forest_pipeline(leaf, trees, stable_seed(seed, split_number, leaf))
            model.fit(x.iloc[fit_index], target[fit_index])
            prediction = model.predict(x.iloc[validation_index])
            scores[leaf].append(balanced_accuracy_score(target[validation_index], prediction))
    return max(scores, key=lambda value: (float(np.mean(scores[value])), -value))


def probability_fields(probabilities: np.ndarray, classes: np.ndarray, truth: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    class_index = {label: index for index, label in enumerate(classes)}
    true_probability = np.array([probabilities[row, class_index[str(label)]] for row, label in enumerate(truth)])
    return probabilities.max(axis=1), true_probability


def classification_metrics(frame: pd.DataFrame) -> dict[str, float]:
    truth = frame["y_true"].astype(str)
    prediction = frame["y_pred"].astype(str)
    return {
        "accuracy": float((truth == prediction).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(truth, prediction)),
        "macro_f1": float(f1_score(truth, prediction, average="macro", zero_division=0)),
        "log_loss": float(-np.log(frame["true_probability"].astype(float).clip(lower=np.finfo(float).eps)).mean()),
    }


def participant_bootstrap(
    frame: pd.DataFrame, value_function, replicates: int, seed: int,
) -> tuple[float, float]:
    participants = np.array(sorted(frame["participant_key"].astype(str).unique()))
    rng = np.random.default_rng(seed)
    estimates = []
    groups = {participant: frame.loc[frame["participant_key"].astype(str) == participant] for participant in participants}
    for _ in range(replicates):
        sampled = rng.choice(participants, size=len(participants), replace=True)
        bootstrap = pd.concat([groups[participant] for participant in sampled], ignore_index=True)
        estimates.append(float(value_function(bootstrap)))
    return tuple(np.quantile(estimates, [0.025, 0.975]))


def config_sha256(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()
