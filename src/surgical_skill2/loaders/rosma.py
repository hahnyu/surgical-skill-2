"""ROSMA kinematics and independently observed error-count loader."""

from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd

from surgical_skill2.loaders.common import hash_parts, strictly_increasing
from surgical_skill2.schema import ArmSeries, Trial


TRIAL_PATTERN = re.compile(r"^(X\d{2})_(Post_and_Sleeve|Pea_on_a_Peg|Wire_Chaser_I)_(\d{2})$")


def read_scores(path: Path) -> dict[str, dict[str, str]]:
    frame = pd.read_csv(path)
    return {str(row["File_name"]): row for row in frame.to_dict(orient="records")}


def load_trial(path: Path, score: dict[str, str]) -> Trial:
    trial_id = path.stem
    match = TRIAL_PATTERN.match(trial_id)
    if match is None:
        raise ValueError(f"invalid ROSMA trial filename: {trial_id}")
    participant, task, repetition = match.group(1), match.group(2), int(match.group(3))
    raw = path.read_bytes()
    columns = [
        "Date",
        "PSM1_position_x", "PSM1_position_y", "PSM1_position_z",
        "PSM2_position_x", "PSM2_position_y", "PSM2_position_z",
    ]
    frame = pd.read_csv(io.BytesIO(raw), usecols=columns)
    timestamps = pd.to_datetime(
        frame["Date"], format="%Y-%m-%d.%H:%M:%S.%f", errors="coerce"
    )
    position_columns = columns[1:]
    finite_positions = np.isfinite(frame[position_columns].to_numpy(dtype=np.float64)).all(axis=1)
    valid = timestamps.notna() & finite_positions
    frame = frame.loc[valid].reset_index(drop=True)
    timestamps = timestamps.loc[valid]
    seconds = (timestamps - timestamps.iloc[0]).dt.total_seconds().to_numpy(dtype=np.float64)
    psm1 = frame[["PSM1_position_x", "PSM1_position_y", "PSM1_position_z"]].to_numpy(dtype=np.float64)
    psm2 = frame[["PSM2_position_x", "PSM2_position_y", "PSM2_position_z"]].to_numpy(dtype=np.float64)
    seconds, psm1, psm2 = strictly_increasing(seconds, psm1, psm2)
    dt = float(np.median(np.diff(seconds)))
    trial = Trial(
        dataset="ROSMA",
        version="10.5281/zenodo.7100542",
        task=task.replace("_", " "),
        participant_source=participant,
        trial_source=trial_id,
        repetition=repetition,
        session=None,
        condition=None,
        outcome_name="Errors",
        outcome_value=float(score["Errors"]),
        outcome_direction="lower_better",
        task_duration_s=float(seconds[-1] - seconds[0] + dt),
        psm1=ArmSeries(seconds, psm1),
        psm2=ArmSeries(seconds, psm2),
        source_sha256=hash_parts(raw),
    )
    trial.validate()
    return trial


def iter_trials(root: Path) -> list[Trial]:
    scores = read_scores(root / "scores.csv")
    trials = []
    for path in sorted(root.glob("X*.csv")):
        if path.stem not in scores:
            raise ValueError(f"ROSMA kinematics has no score row: {path.stem}")
        trials.append(load_trial(path, scores[path.stem]))
    if len(trials) != 206:
        raise ValueError(f"expected 206 matched ROSMA trials, got {len(trials)}")
    return trials
