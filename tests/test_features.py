import numpy as np

from surgical_skill2.features import extract_features
from surgical_skill2.schema import ArmSeries, Trial


def make_trial() -> Trial:
    t = np.arange(6, dtype=float)
    left = np.column_stack((t, np.zeros_like(t), np.zeros_like(t)))
    right = np.column_stack((np.zeros_like(t), t * 2, np.zeros_like(t)))
    return Trial(
        dataset="fixture", version="1", task="task", participant_source="person",
        trial_source="trial", repetition=1, session=None, condition=None,
        outcome_name="value", outcome_value=2.0, outcome_direction="lower_better",
        task_duration_s=6.0,
        psm1=ArmSeries(t, left, t / 5), psm2=ArmSeries(t, right, t / 5),
        source_sha256="0" * 64,
    )


def test_known_linear_trajectory_features_are_exact():
    row = extract_features(make_trial())
    assert row["duration_s"] == 6.0
    assert row["psm1_path_length_m"] == 5.0
    assert row["psm2_path_length_m"] == 10.0
    assert row["psm1_speed_mean_m_s"] == 1.0
    assert row["psm2_speed_mean_m_s"] == 2.0
    assert row["psm1_accel_abs_mean_m_s2"] == 0.0
    assert row["psm1_jerk_abs_mean_m_s3"] == 0.0
    assert row["bimanual_speed_correlation"] == 0.0
    assert np.isclose(row["path_length_asymmetry"], 1 / 3)


def test_features_are_bitwise_deterministic_for_same_trial():
    first = extract_features(make_trial())
    second = extract_features(make_trial())
    assert first == second


def test_recording_gap_is_reported_and_not_counted_as_motion():
    t = np.array([0, 1, 2, 3, 4, 12, 13, 14, 15, 16], dtype=float)
    position = np.column_stack((np.array([0, 1, 2, 3, 4, 100, 101, 102, 103, 104]), np.zeros(10), np.zeros(10)))
    base = make_trial()
    trial = Trial(
        dataset=base.dataset, version=base.version, task=base.task,
        participant_source=base.participant_source, trial_source=base.trial_source,
        repetition=base.repetition, session=base.session, condition=base.condition,
        outcome_name=base.outcome_name, outcome_value=base.outcome_value,
        outcome_direction=base.outcome_direction, task_duration_s=17.0,
        psm1=ArmSeries(t, position), psm2=ArmSeries(t, position),
        source_sha256=base.source_sha256,
    )
    row = extract_features(trial)
    assert row["psm1_path_length_m"] == 8.0
    assert row["psm1_gap_fraction"] == 0.5
