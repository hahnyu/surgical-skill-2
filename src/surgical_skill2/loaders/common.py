"""Shared loader helpers."""

from __future__ import annotations

from hashlib import sha256

import numpy as np

from surgical_skill2.schema import ArmSeries


def hash_parts(*parts: bytes) -> str:
    digest = sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def strictly_increasing(timestamps: np.ndarray, *arrays: np.ndarray) -> tuple[np.ndarray, ...]:
    """Drop duplicate/backward timestamps while preserving the first sample."""
    timestamps = np.asarray(timestamps, dtype=np.float64)
    keep = np.concatenate(([True], np.diff(timestamps) > 0))
    return (timestamps[keep], *(np.asarray(array)[keep] for array in arrays))


def trim_arm(arm: ArmSeries, start_s: float, end_s: float) -> ArmSeries:
    keep = (arm.timestamps_s >= start_s) & (arm.timestamps_s <= end_s)
    if keep.sum() < 4:
        raise ValueError("task window contains fewer than four position samples")
    gripper = None if arm.gripper is None else arm.gripper[keep]
    return ArmSeries(arm.timestamps_s[keep], arm.position_m[keep], gripper)


def align_optional_signal(
    target_timestamps: np.ndarray,
    signal_timestamps: np.ndarray,
    signal_values: np.ndarray,
) -> np.ndarray:
    t, values = strictly_increasing(signal_timestamps, signal_values)
    return np.interp(target_timestamps, t, values)

