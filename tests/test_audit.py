import numpy as np
import pandas as pd
import pytest

from surgical_skill2.audit import (
    assert_no_leakage_columns,
    available_features,
    inner_splits,
    regression_pipeline,
)


def test_leakage_canary_is_rejected():
    with pytest.raises(ValueError, match="forbidden"):
        assert_no_leakage_columns(["duration_s", "participant_code"])


def test_feature_allowlist_excludes_metadata_and_target():
    frame = pd.DataFrame({"duration_s": [1.0, 2.0], "outcome_value": [3.0, 4.0]})
    assert available_features(frame, duration_only=True) == ["duration_s"]


def test_held_out_inner_splits_never_share_participants():
    frame = pd.DataFrame({"participant_key": np.repeat(list("abcd"), 3)})
    for train, validation in inner_splits(frame, "held_out_participant"):
        assert set(frame.iloc[train].participant_key).isdisjoint(frame.iloc[validation].participant_key)


def test_scaler_uses_training_rows_only():
    x_train = pd.DataFrame({"duration_s": [1.0, 2.0, 3.0]})
    y_train = np.array([1.0, 2.0, 3.0])
    model = regression_pipeline(1.0).fit(x_train, y_train)
    before = model.named_steps["model"].regressor_.named_steps["scale"].mean_.copy()
    model.predict(pd.DataFrame({"duration_s": [1_000_000.0]}))
    after = model.named_steps["model"].regressor_.named_steps["scale"].mean_
    np.testing.assert_array_equal(before, after)
