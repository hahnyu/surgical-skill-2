"""Training-fold-only linear identity interventions and matched controls."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler

from .audit import HARMONIZED_FEATURE_COLUMNS, inner_splits, logistic_pipeline, stable_seed


class FeatureTransformer:
    def fit(self, frame: pd.DataFrame, identity: np.ndarray | None = None) -> "FeatureTransformer":
        raise NotImplementedError

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError


@dataclass
class StandardizedFeatures(FeatureTransformer):
    columns: list[str]

    def fit(self, frame: pd.DataFrame, identity: np.ndarray | None = None) -> "StandardizedFeatures":
        self.imputer = SimpleImputer(strategy="median").fit(frame[self.columns])
        values = self.imputer.transform(frame[self.columns])
        self.scaler = StandardScaler().fit(values)
        return self

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        return self.scaler.transform(self.imputer.transform(frame[self.columns]))


@dataclass
class DurationResidualizer(FeatureTransformer):
    columns: list[str]

    def fit(self, frame: pd.DataFrame, identity: np.ndarray | None = None) -> "DurationResidualizer":
        if "duration_s" not in self.columns:
            raise ValueError("duration residualization requires duration_s")
        self.output_columns = [column for column in self.columns if column != "duration_s"]
        self.imputer = SimpleImputer(strategy="median").fit(frame[self.columns])
        values = self.imputer.transform(frame[self.columns])
        duration_index = self.columns.index("duration_s")
        output_indices = [self.columns.index(column) for column in self.output_columns]
        design = np.column_stack((np.ones(len(values)), values[:, duration_index]))
        self.coefficients = np.linalg.lstsq(design, values[:, output_indices], rcond=None)[0]
        residual = values[:, output_indices] - design @ self.coefficients
        self.scaler = StandardScaler().fit(residual)
        return self

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        values = self.imputer.transform(frame[self.columns])
        duration_index = self.columns.index("duration_s")
        output_indices = [self.columns.index(column) for column in self.output_columns]
        design = np.column_stack((np.ones(len(values)), values[:, duration_index]))
        residual = values[:, output_indices] - design @ self.coefficients
        return self.scaler.transform(residual)


@dataclass
class IdentitySubspaceRemover(FeatureTransformer):
    columns: list[str]
    k: int
    c_value: float = 1.0

    def fit(self, frame: pd.DataFrame, identity: np.ndarray | None = None) -> "IdentitySubspaceRemover":
        if identity is None:
            raise ValueError("identity labels are required")
        self.base = StandardizedFeatures(self.columns).fit(frame)
        values = self.base.transform(frame)
        classifier = LogisticRegression(C=self.c_value, solver="lbfgs", max_iter=5000).fit(values, identity)
        _, _, right = np.linalg.svd(classifier.coef_, full_matrices=False)
        usable = min(self.k, len(right))
        self.directions = right[:usable]
        return self

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        values = self.base.transform(frame)
        if not len(self.directions):
            return values
        return values - (values @ self.directions.T) @ self.directions


@dataclass
class RandomSubspaceRemover(FeatureTransformer):
    columns: list[str]
    k: int
    seed: int

    def fit(self, frame: pd.DataFrame, identity: np.ndarray | None = None) -> "RandomSubspaceRemover":
        self.base = StandardizedFeatures(self.columns).fit(frame)
        dimension = len(self.columns)
        usable = min(self.k, dimension)
        if usable:
            rng = np.random.default_rng(self.seed)
            q, _ = np.linalg.qr(rng.normal(size=(dimension, usable)))
            self.directions = q.T
        else:
            self.directions = np.empty((0, dimension))
        return self

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        values = self.base.transform(frame)
        if not len(self.directions):
            return values
        return values - (values @ self.directions.T) @ self.directions


def finite_columns(frame: pd.DataFrame, requested: list[str] | None = None) -> list[str]:
    requested = HARMONIZED_FEATURE_COLUMNS if requested is None else requested
    return [column for column in requested if np.isfinite(pd.to_numeric(frame[column], errors="coerce")).any()]


def _array_identity_score(
    train_values: np.ndarray, validation_values: np.ndarray,
    train_identity: np.ndarray, validation_identity: np.ndarray,
) -> float:
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=5000).fit(train_values, train_identity)
    return float(balanced_accuracy_score(validation_identity, model.predict(validation_values)))


def choose_identity_k(
    train: pd.DataFrame,
    task_target: np.ndarray | None,
    task_protocol: str,
    k_grid: list[int],
    utility_margin: float,
    columns: list[str],
    identity_fold_column: str = "identity_fold",
) -> tuple[int, dict[int, dict[str, float]]]:
    identity = train["participant_key"].astype(str).to_numpy()
    max_rank = min(len(columns), len(np.unique(identity)) - 1)
    candidates = sorted({min(int(k), max_rank) for k in k_grid})
    identity_frame = train.copy()
    identity_frame["test_fold"] = identity_frame[identity_fold_column]
    identity_cv = inner_splits(identity_frame, "same_participant")
    task_cv = inner_splits(train, task_protocol) if task_target is not None else []
    results: dict[int, dict[str, float]] = {}
    for k in candidates:
        identity_scores = []
        for fit_index, validation_index in identity_cv:
            transformer = IdentitySubspaceRemover(columns, k).fit(
                train.iloc[fit_index], identity[fit_index]
            )
            identity_scores.append(_array_identity_score(
                transformer.transform(train.iloc[fit_index]),
                transformer.transform(train.iloc[validation_index]),
                identity[fit_index], identity[validation_index],
            ))
        task_scores = []
        if task_target is not None:
            for fit_index, validation_index in task_cv:
                transformer = IdentitySubspaceRemover(columns, k).fit(
                    train.iloc[fit_index], identity[fit_index]
                )
                model = Ridge(alpha=10.0).fit(
                    transformer.transform(train.iloc[fit_index]), task_target[fit_index]
                )
                task_scores.append(mean_absolute_error(
                    task_target[validation_index], model.predict(transformer.transform(train.iloc[validation_index]))
                ))
        results[k] = {
            "identity_balanced_accuracy": float(np.mean(identity_scores)),
            "task_mae": float(np.mean(task_scores)) if task_scores else float("nan"),
        }
    if task_target is None:
        chosen = min(candidates, key=lambda k: (results[k]["identity_balanced_accuracy"], k))
    else:
        baseline = results[0]["task_mae"]
        margin = utility_margin * float(np.std(task_target))
        allowed = [k for k in candidates if results[k]["task_mae"] <= baseline + margin]
        chosen = min(allowed, key=lambda k: (results[k]["identity_balanced_accuracy"], k))
    return chosen, results
