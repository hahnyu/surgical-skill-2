from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("phase5", ROOT / "scripts" / "build_phase5_analysis.py")
phase5 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(phase5)


def test_outer_training_sd_excludes_complete_test_fold() -> None:
    frame = pd.DataFrame({
        "dataset": ["D"] * 4,
        "task": ["T"] * 4,
        "protocol": ["held_out_participant"] * 4,
        "test_fold": ["a", "a", "b", "b"],
        "trial_key": ["1", "2", "3", "4"],
        "y_true": [0.0, 2.0, 10.0, 14.0],
    })
    result = phase5.outer_training_sd(frame)
    assert result.iloc[0] == result.iloc[1]
    assert result.iloc[2] == result.iloc[3]
    assert result.iloc[0] == pd.Series([10.0, 14.0]).std(ddof=1)
    assert result.iloc[2] == pd.Series([0.0, 2.0]).std(ddof=1)


def test_bootstrap_is_participant_level_and_deterministic() -> None:
    frame = pd.DataFrame({
        "dataset": ["D"] * 3,
        "task": ["T"] * 3,
        "participant_key": ["p1", "p2", "p3"],
        "value": [1.0, 2.0, 6.0],
    })
    summary1, draws1 = phase5.bootstrap_rows(frame, ["dataset", "task"], "value", "test", 50, 7)
    summary2, draws2 = phase5.bootstrap_rows(frame, ["dataset", "task"], "value", "test", 50, 7)
    pd.testing.assert_frame_equal(summary1, summary2)
    pd.testing.assert_frame_equal(draws1, draws2)
    assert summary1.loc[0, "estimate"] == 3.0
    assert summary1.loc[0, "participants"] == 3
