import numpy as np
import pandas as pd

from surgical_skill2.interventions import (
    DurationResidualizer,
    IdentitySubspaceRemover,
    RandomSubspaceRemover,
)


def fixture():
    duration = np.arange(1, 21, dtype=float)
    return pd.DataFrame({
        "duration_s": duration,
        "signal": 3.0 * duration + np.tile([-1.0, 1.0], 10),
        "identity_feature": np.repeat([-2.0, 2.0], 10),
    })


def test_duration_residualizer_uses_training_rows_and_removes_linear_duration():
    frame = fixture()
    transformer = DurationResidualizer(["duration_s", "signal"]).fit(frame.iloc[:15])
    before = transformer.coefficients.copy()
    transformed = transformer.transform(frame)
    np.testing.assert_array_equal(before, transformer.coefficients)
    assert abs(np.corrcoef(transformed[:, 0], frame.duration_s)[0, 1]) < 0.15


def test_identity_subspace_removal_reduces_fitted_identity_direction():
    frame = fixture()
    identity = np.array(["a"] * 10 + ["b"] * 10)
    transformer = IdentitySubspaceRemover(list(frame.columns), 1).fit(frame, identity)
    projected = transformer.transform(frame)
    direction = transformer.directions[0]
    assert np.max(np.abs(projected @ direction)) < 1e-10


def test_identity_projection_is_unchanged_by_outer_test_values():
    frame = fixture()
    train = frame.iloc[:15].copy()
    identity = np.array(["a"] * 10 + ["b"] * 5)
    first = IdentitySubspaceRemover(list(frame.columns), 1).fit(train, identity)
    perturbed_test = frame.iloc[15:].copy() * 1_000_000
    first.transform(perturbed_test)
    second = IdentitySubspaceRemover(list(frame.columns), 1).fit(train, identity)
    np.testing.assert_array_equal(first.directions, second.directions)


def test_random_projection_is_fixed_by_seed_and_training_data_only():
    frame = fixture()
    first = RandomSubspaceRemover(list(frame.columns), 1, 7).fit(frame.iloc[:15])
    second = RandomSubspaceRemover(list(frame.columns), 1, 7).fit(frame.iloc[:15])
    np.testing.assert_array_equal(first.directions, second.directions)
    np.testing.assert_array_equal(first.transform(frame), second.transform(frame))
