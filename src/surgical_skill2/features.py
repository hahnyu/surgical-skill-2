"""Deterministic harmonized kinematic summaries computed from positions."""

from __future__ import annotations

import numpy as np

from .schema import ArmSeries, Trial


IDLE_THRESHOLD_M_S = 0.001


def _sample_rate(timestamps: np.ndarray) -> float:
    dt = np.diff(timestamps)
    return float(1.0 / np.median(dt))


def _valid_step_mask(arm: ArmSeries) -> np.ndarray:
    dt = np.diff(arm.timestamps_s)
    return dt <= 3.0 * np.median(dt)


def _speed(arm: ArmSeries) -> np.ndarray:
    dt = np.diff(arm.timestamps_s)
    values = np.linalg.norm(np.diff(arm.position_m, axis=0), axis=1) / dt
    values[~_valid_step_mask(arm)] = np.nan
    return values


def _acceleration(arm: ArmSeries) -> np.ndarray:
    speed = _speed(arm)
    mid = (arm.timestamps_s[:-1] + arm.timestamps_s[1:]) / 2.0
    return np.diff(speed) / np.diff(mid)


def _jerk(arm: ArmSeries) -> np.ndarray:
    acceleration = _acceleration(arm)
    mid = (arm.timestamps_s[:-1] + arm.timestamps_s[1:]) / 2.0
    accel_time = (mid[:-1] + mid[1:]) / 2.0
    return np.diff(acceleration) / np.diff(accel_time)


def _arm_features(prefix: str, arm: ArmSeries) -> dict[str, float]:
    speed = _speed(arm)
    acceleration = np.abs(_acceleration(arm))
    jerk = np.abs(_jerk(arm))
    speed = speed[np.isfinite(speed)]
    acceleration = acceleration[np.isfinite(acceleration)]
    jerk = jerk[np.isfinite(jerk)]
    step = np.linalg.norm(np.diff(arm.position_m, axis=0), axis=1)
    valid_step = _valid_step_mask(arm)
    span = np.ptp(arm.position_m, axis=0)
    values: dict[str, float] = {
        f"{prefix}_path_length_m": float(step[valid_step].sum()),
        f"{prefix}_speed_mean_m_s": float(speed.mean()),
        f"{prefix}_speed_std_m_s": float(speed.std()),
        f"{prefix}_speed_q10_m_s": float(np.quantile(speed, 0.10)),
        f"{prefix}_speed_q50_m_s": float(np.quantile(speed, 0.50)),
        f"{prefix}_speed_q90_m_s": float(np.quantile(speed, 0.90)),
        f"{prefix}_accel_abs_mean_m_s2": float(acceleration.mean()),
        f"{prefix}_accel_abs_q90_m_s2": float(np.quantile(acceleration, 0.90)),
        f"{prefix}_jerk_abs_mean_m_s3": float(jerk.mean()),
        f"{prefix}_jerk_abs_q90_m_s3": float(np.quantile(jerk, 0.90)),
        f"{prefix}_idle_fraction": float((speed < IDLE_THRESHOLD_M_S).mean()),
        f"{prefix}_workspace_bbox_m3": float(np.prod(span)),
        f"{prefix}_gap_fraction": float(np.diff(arm.timestamps_s)[~valid_step].sum() / max(arm.timestamps_s[-1] - arm.timestamps_s[0], np.finfo(float).eps)),
    }
    if arm.gripper is not None:
        values.update(
            {
                f"{prefix}_gripper_mean": float(np.mean(arm.gripper)),
                f"{prefix}_gripper_std": float(np.std(arm.gripper)),
                f"{prefix}_gripper_range": float(np.ptp(arm.gripper)),
                f"{prefix}_gripper_total_variation": float(np.abs(np.diff(arm.gripper))[valid_step].sum()),
            }
        )
    else:
        values.update(
            {
                f"{prefix}_gripper_mean": float("nan"),
                f"{prefix}_gripper_std": float("nan"),
                f"{prefix}_gripper_range": float("nan"),
                f"{prefix}_gripper_total_variation": float("nan"),
            }
        )
    return values


def _aligned_speed_correlation(left: ArmSeries, right: ArmSeries) -> float:
    start = max(left.timestamps_s[0], right.timestamps_s[0])
    end = min(left.timestamps_s[-1], right.timestamps_s[-1])
    rate = min(_sample_rate(left.timestamps_s), _sample_rate(right.timestamps_s))
    count = int(np.floor((end - start) * rate)) + 1
    if count < 4:
        raise ValueError("instrument streams do not have a sufficient common interval")
    grid = start + np.arange(count, dtype=np.float64) / rate
    left_pos = np.column_stack(
        [np.interp(grid, left.timestamps_s, left.position_m[:, axis]) for axis in range(3)]
    )
    right_pos = np.column_stack(
        [np.interp(grid, right.timestamps_s, right.position_m[:, axis]) for axis in range(3)]
    )
    left_speed = np.linalg.norm(np.diff(left_pos, axis=0), axis=1) * rate
    right_speed = np.linalg.norm(np.diff(right_pos, axis=0), axis=1) * rate
    def near_observation(source: np.ndarray) -> np.ndarray:
        indices = np.searchsorted(source, grid)
        lower = np.clip(indices - 1, 0, len(source) - 1)
        upper = np.clip(indices, 0, len(source) - 1)
        distance = np.minimum(np.abs(grid - source[lower]), np.abs(grid - source[upper]))
        return distance <= 2.5 / rate

    observed = near_observation(left.timestamps_s) & near_observation(right.timestamps_s)
    valid_steps = observed[:-1] & observed[1:]
    left_speed = left_speed[valid_steps]
    right_speed = right_speed[valid_steps]
    if len(left_speed) < 3:
        raise ValueError("too few aligned observed samples for bimanual correlation")
    if left_speed.std() == 0 or right_speed.std() == 0:
        return 0.0
    return float(np.corrcoef(left_speed, right_speed)[0, 1])


def extract_features(trial: Trial) -> dict[str, float | int | str | None]:
    """Return identifiers, design fields, outcome, and fixed summary features."""
    trial.validate()
    psm1 = _arm_features("psm1", trial.psm1)
    psm2 = _arm_features("psm2", trial.psm2)
    path_asymmetry = abs(psm1["psm1_path_length_m"] - psm2["psm2_path_length_m"]) / max(
        psm1["psm1_path_length_m"] + psm2["psm2_path_length_m"], np.finfo(float).eps
    )
    row: dict[str, float | int | str | None] = {
        "dataset": trial.dataset,
        "version": trial.version,
        "task": trial.task,
        "participant_key": trial.participant_key,
        "trial_key": trial.trial_key,
        "repetition": trial.repetition,
        "session": trial.session,
        "condition": trial.condition,
        "outcome_name": trial.outcome_name,
        "outcome_value": trial.outcome_value,
        "outcome_direction": trial.outcome_direction,
        "source_sha256": trial.source_sha256,
        "duration_s": trial.task_duration_s,
        "psm1_samples": len(trial.psm1.timestamps_s),
        "psm2_samples": len(trial.psm2.timestamps_s),
        "psm1_sampling_hz": _sample_rate(trial.psm1.timestamps_s),
        "psm2_sampling_hz": _sample_rate(trial.psm2.timestamps_s),
        "bimanual_speed_correlation": _aligned_speed_correlation(trial.psm1, trial.psm2),
        "path_length_asymmetry": float(path_asymmetry),
    }
    row.update(psm1)
    row.update(psm2)
    return row
