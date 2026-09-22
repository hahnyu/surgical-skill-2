"""Deterministic loader for the authorized local JIGSAWS release."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from surgical_skill2.loaders.common import hash_parts
from surgical_skill2.schema import ArmSeries, Trial


TASKS = ("Suturing", "Knot_Tying", "Needle_Passing")
EXPECTED = {"Suturing": 39, "Knot_Tying": 36, "Needle_Passing": 28}
FPS = 30.0
TRIAL_PATTERN = re.compile(r"^(Suturing|Knot_Tying|Needle_Passing)_([A-I])(\d{3})$")


def _window(root: Path, task: str, trial_id: str) -> tuple[int, int, bytes]:
    path = root / task / "transcriptions" / f"{trial_id}.txt"
    raw = path.read_bytes()
    bounds = [line.split()[:2] for line in raw.decode().splitlines() if len(line.split()) >= 2]
    if not bounds:
        raise ValueError(f"empty transcription: {path}")
    return min(int(row[0]) for row in bounds), max(int(row[1]) for row in bounds), raw


def iter_trials(root: Path) -> list[Trial]:
    trials: list[Trial] = []
    for task in TASKS:
        meta_path = root / task / f"meta_file_{task}.txt"
        meta_raw = meta_path.read_bytes()
        task_count = 0
        for line in meta_raw.decode().splitlines():
            parts = line.split()
            if len(parts) < 9:
                continue
            trial_id, skill = parts[0], parts[1]
            grs = int(parts[2])
            elements = [int(value) for value in parts[3:9]]
            if grs != sum(elements):
                raise ValueError(f"{trial_id}: GRS does not equal the six elements")
            match = TRIAL_PATTERN.match(trial_id)
            if match is None:
                raise ValueError(f"invalid JIGSAWS trial ID: {trial_id}")
            participant, repetition = match.group(2), int(match.group(3))
            kin_path = root / task / "kinematics" / "AllGestures" / f"{trial_id}.txt"
            kin_raw = kin_path.read_bytes()
            matrix = np.loadtxt(kin_path, dtype=np.float64)
            if matrix.ndim != 2 or matrix.shape[1] != 76:
                raise ValueError(f"{trial_id}: expected 76 kinematic columns")
            start, end, transcription_raw = _window(root, task, trial_id)
            windowed = matrix[start - 1 : end]
            timestamps = np.arange(len(windowed), dtype=np.float64) / FPS
            trial = Trial(
                dataset="JIGSAWS",
                version="paper1-local-authorized-copy",
                task=task.replace("_", " "),
                participant_source=participant,
                trial_source=trial_id,
                repetition=repetition,
                session=None,
                condition=f"self_declared_skill_{skill}",
                outcome_name="GRS",
                outcome_value=float(grs),
                outcome_direction="higher_better",
                task_duration_s=len(windowed) / FPS,
                psm1=ArmSeries(timestamps, windowed[:, 38:41], windowed[:, 56]),
                psm2=ArmSeries(timestamps, windowed[:, 57:60], windowed[:, 75]),
                source_sha256=hash_parts(meta_raw, transcription_raw, kin_raw),
            )
            trial.validate()
            trials.append(trial)
            task_count += 1
        if task_count != EXPECTED[task]:
            raise ValueError(f"{task}: expected {EXPECTED[task]} trials, got {task_count}")
    if len(trials) != 103:
        raise ValueError(f"expected 103 JIGSAWS trials, got {len(trials)}")
    return trials

