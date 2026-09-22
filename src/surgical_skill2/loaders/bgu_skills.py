"""BGU-SKILLS loader with source-defined task windows and exclusions."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from surgical_skill2.loaders.common import hash_parts, strictly_increasing
from surgical_skill2.schema import ArmSeries, Trial


NAME_PATTERN = re.compile(
    r"^([A-U])_([1-6])_([abc])_(Knottying|Ringtowertransfer|Suturing)_kinematics\.csv$"
)
TASK_LABELS = {
    "Knottying": "Knot Tying",
    "Ringtowertransfer": "Ring Tower Transfer",
    "Suturing": "Suturing",
}
FILE_SPECS = {
    "Knottying": ("Knottying_Annotations_StartFinish_Events.csv", "NotesKnotTying.csv"),
    "Ringtowertransfer": ("Ringtowertransfer_Annotations_StartFinish_Events.csv", "NotesRingTowerTransfer.csv"),
    "Suturing": ("Suturing_Annotations_StartFinish_Events.csv", "NotesSuturing.csv"),
}
EXPECTED_INCLUDED = {"Knottying": 311, "Ringtowertransfer": 312, "Suturing": 315}


def read_annotations(path: Path) -> dict[tuple[str, int, str, str], tuple[float, float]]:
    frame = pd.read_csv(path)
    windows = {}
    for key, group in frame.groupby(["Participant", "Round", "Session", "Task"], sort=True):
        starts = group.loc[group["Event"] == "Start Task", "TimeStamp"]
        finishes = group.loc[group["Event"] == "Finish Task", "TimeStamp"]
        if len(starts) and len(finishes):
            windows[(str(key[0]), int(key[1]), str(key[2]), str(key[3]))] = (
                float(starts.min()), float(finishes.max())
            )
    return windows


def read_inclusion(path: Path) -> dict[str, bool]:
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)
    first, second = frame.columns[:2]
    return {str(row[first]): int(row[second]) == 1 for _, row in frame.iterrows()}


def load_trial_bytes(raw: bytes, filename: str, start_s: float, end_s: float) -> Trial:
    match = NAME_PATTERN.match(Path(filename).name)
    if match is None:
        raise ValueError(f"invalid BGU-SKILLS filename: {filename}")
    participant, shift, session, task = match.groups()
    usecols = [
        "Timestamp", "Time",
        "psm1_position_1", "psm1_position_2", "psm1_position_3", "psm1_jaw_1",
        "psm2_position_1", "psm2_position_2", "psm2_position_3", "psm2_jaw_1",
    ]
    frame = pd.read_csv(io.BytesIO(raw), usecols=usecols)
    frame = frame.loc[(frame["Timestamp"] >= start_s) & (frame["Timestamp"] <= end_s)].copy()
    frame = frame.dropna(subset=usecols).reset_index(drop=True)
    timestamps = frame["Timestamp"].to_numpy(dtype=np.float64)
    psm1 = frame[["psm1_position_1", "psm1_position_2", "psm1_position_3"]].to_numpy(dtype=np.float64)
    psm2 = frame[["psm2_position_1", "psm2_position_2", "psm2_position_3"]].to_numpy(dtype=np.float64)
    jaw1 = frame["psm1_jaw_1"].to_numpy(dtype=np.float64)
    jaw2 = frame["psm2_jaw_1"].to_numpy(dtype=np.float64)
    timestamps, psm1, psm2, jaw1, jaw2 = strictly_increasing(timestamps, psm1, psm2, jaw1, jaw2)
    trial_id = f"{participant}_{shift}_{session}_{task}"
    trial = Trial(
        dataset="BGU-SKILLS",
        version="1.0",
        task=TASK_LABELS[task],
        participant_source=participant,
        trial_source=trial_id,
        repetition=int(shift),
        session=session,
        condition=f"shift_{shift}_{session}",
        outcome_name=None,
        outcome_value=None,
        outcome_direction=None,
        task_duration_s=end_s - start_s,
        psm1=ArmSeries(timestamps, psm1, jaw1),
        psm2=ArmSeries(timestamps, psm2, jaw2),
        source_sha256=hash_parts(raw),
    )
    trial.validate()
    return trial


def iter_trials(root: Path) -> list[Trial]:
    trials: list[Trial] = []
    for task, label in TASK_LABELS.items():
        annotation_name, notes_name = FILE_SPECS[task]
        annotation = root / annotation_name
        notes = root / notes_name
        archive = root / f"{task}_Kinematics.zip"
        windows = read_annotations(annotation)
        inclusion = read_inclusion(notes)
        count = 0
        with zipfile.ZipFile(archive) as zipped:
            members = sorted(
                (info for info in zipped.infolist() if info.filename.endswith("_kinematics.csv")),
                key=lambda info: info.filename,
            )
            if len(members) != 324:
                raise ValueError(f"{task}: expected 324 kinematics members, got {len(members)}")
            for member in members:
                match = NAME_PATTERN.match(Path(member.filename).name)
                if match is None:
                    raise ValueError(member.filename)
                participant, shift, session, parsed_task = match.groups()
                short_key = f"{participant}_{shift}_{session}"
                if not inclusion.get(short_key, False):
                    continue
                key = (participant, int(shift), session, parsed_task)
                if key not in windows:
                    raise ValueError(f"included trial has no complete task window: {key}")
                start, end = windows[key]
                trials.append(load_trial_bytes(zipped.read(member), member.filename, start, end))
                count += 1
        if count != EXPECTED_INCLUDED[task]:
            raise ValueError(f"{task}: expected {EXPECTED_INCLUDED[task]} included trials, got {count}")
    if len(trials) != 938:
        raise ValueError(f"expected 938 BGU-SKILLS trials, got {len(trials)}")
    return trials
