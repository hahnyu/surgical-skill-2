"""BGU-PatCut scan-error and task-windowed dVRK loader."""

from __future__ import annotations

import io
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

# mat-io imports h5py even for MATLAB v5 files. PatCut uses v5 exclusively;
# provide the small import-time surface so the unused HDF5 extension is never
# loaded. This avoids an unnecessary native-library dependency in extraction.
if "h5py" not in sys.modules:
    h5py_stub = types.ModuleType("h5py")
    h5py_stub.__version__ = "not-loaded-v5-only"
    h5py_stub.File = type("UnavailableH5File", (), {})
    h5py_stub.Group = type("UnavailableH5Group", (), {})
    h5py_stub.Dataset = type("UnavailableH5Dataset", (), {})
    h5py_stub.Reference = type("UnavailableH5Reference", (), {})
    h5py_stub.ref_dtype = np.dtype("O")
    h5py_stub.special_dtype = lambda **_: np.dtype("O")
    sys.modules["h5py"] = h5py_stub

from matio import load_from_mat
from scipy.io import loadmat

from surgical_skill2.loaders.common import align_optional_signal, hash_parts, trim_arm
from surgical_skill2.schema import ArmSeries, Trial


ASSIGNMENT = {
    "force": {
        "28061013": 1, "29061018": 0, "29061337": 1, "01071039": 0,
        "02071017": 1, "06071407": 1, "15071540": 0, "19071017": 1,
        "19071311": 0, "16081118": 0, "16081642": 1, "17081026": 1,
        "17081344": 0, "18081021": 1, "18081318": 0, "09091043": 0,
        "09091325": 0, "09091621": 1, "10091019": 1, "10091311": 0,
        "13091033": 0, "13091336": 1, "13091632": 0, "14091031": 1,
        "15091405": 1, "15091653": 0, "16091042": 0, "16091312": 1,
        "17091119": 1, "17091442": 0,
    },
    "motion": {
        "07061254": 1, "11060830": 0, "11061250": 1, "14061115": 0,
        "15061420": 1, "17061200": 1, "17061500": 0, "18061013": 0,
        "21061437": 1, "29110917": 1, "02120927": 1, "06121320": 0,
        "09120924": 1, "16120950": 0, "20120941": 0, "21021346": 1,
        "22021028": 0, "22021457": 0, "01030929": 1, "08031031": 1,
        "14031539": 0, "12041012": 0, "18041607": 1, "25040946": 0,
    },
}
EXPECTED = {"force": 700, "motion": 554}


def _point_name(value: object) -> str:
    if isinstance(value, np.ndarray) and value.size == 1:
        value = value.item()
    return str(value).strip("[]'\" ")


def _unwrap_stream(value: object) -> tuple[np.ndarray, np.ndarray]:
    while isinstance(value, np.ndarray) and value.dtype == object and value.size == 1:
        value = value.item()
    if not isinstance(value, dict) or "data" not in value or "timestamps" not in value:
        raise ValueError("unexpected PatCut stream structure")
    return np.asarray(value["timestamps"], dtype=np.float64), np.asarray(value["data"], dtype=np.float64)


def _arm(data: dict, name: str) -> ArmSeries:
    position_t, position = _unwrap_stream(data[name]["position"])
    jaw_t, jaw = _unwrap_stream(data[name]["jaw"])
    gripper = align_optional_signal(position_t, jaw_t, jaw.reshape(-1))
    return ArmSeries(position_t, position, gripper)


def read_accuracy(path: Path) -> tuple[pd.DataFrame, bytes]:
    raw = path.read_bytes()
    frame = load_from_mat(path)["AccuracyResults"]
    required = {"Trial", "TotalErrors", "TotalErrorsInside", "TotalErrorsOutside"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{path}: missing accuracy columns")
    if not np.allclose(frame["TotalErrors"], frame["TotalErrorsInside"] + frame["TotalErrorsOutside"]):
        raise ValueError(f"{path}: TotalErrors does not equal inside + outside")
    return frame, raw


def read_windows(path: Path) -> tuple[dict[int, tuple[float, float]], bytes]:
    raw = path.read_bytes()
    frame = load_from_mat(path)["Segmentation"].copy()
    frame["point"] = frame["PointName"].map(_point_name)
    windows = {}
    for trial, group in frame.groupby("Trial", sort=True):
        starts = group.loc[group["point"] == "StartTime", "TimeStamp"]
        finishes = group.loc[group["point"] == "FinishTime", "TimeStamp"]
        if len(starts) != 1 or len(finishes) != 1:
            raise ValueError(f"{path}: trial {trial} lacks one StartTime and FinishTime")
        windows[int(trial)] = (float(starts.iloc[0]), float(finishes.iloc[0]))
    return windows, raw


def load_trial_bytes(
    raw: bytes,
    participant: str,
    trial_number: int,
    experiment: str,
    outcome_row: pd.Series,
    window: tuple[float, float],
    accuracy_raw: bytes,
    segmentation_raw: bytes,
) -> Trial:
    data = loadmat(io.BytesIO(raw), simplify_cells=True)["dvrkData"]
    start, end = window
    psm1 = trim_arm(_arm(data, "psm1"), start, end)
    psm2 = trim_arm(_arm(data, "psm2"), start, end)
    stage = "baseline" if trial_number <= 5 else "training" if trial_number <= 15 else "post"
    assignment = "experimental" if ASSIGNMENT[experiment][participant] else "control"
    trial_id = f"{experiment}_{participant}_{trial_number:02d}"
    trial = Trial(
        dataset="BGU-PatCut",
        version="2.1",
        task="Pattern Cutting",
        participant_source=f"{experiment}_{participant}",
        trial_source=trial_id,
        repetition=trial_number,
        session=stage,
        condition=f"{experiment}_{assignment}",
        outcome_name="TE",
        outcome_value=float(outcome_row["TotalErrors"]),
        outcome_direction="lower_better",
        task_duration_s=end - start,
        psm1=psm1,
        psm2=psm2,
        source_sha256=hash_parts(raw, accuracy_raw, segmentation_raw),
    )
    trial.validate()
    return trial


def iter_trials(root: Path) -> list[Trial]:
    trials: list[Trial] = []
    for experiment in ("force", "motion"):
        experiment_root = root / experiment
        count = 0
        for participant_root in sorted(path for path in experiment_root.iterdir() if path.is_dir()):
            participant = participant_root.name
            if participant not in ASSIGNMENT[experiment]:
                raise ValueError(f"unknown {experiment} participant: {participant}")
            accuracy_path = participant_root / f"subj_{participant}_AccuracyResults.mat"
            segmentation_path = participant_root / f"subj_{participant}_Segmentation.mat"
            accuracy, accuracy_raw = read_accuracy(accuracy_path)
            windows, segmentation_raw = read_windows(segmentation_path)
            outcome_rows = {int(row.Trial): row for _, row in accuracy.iterrows()}
            for path in sorted(participant_root.glob(f"subj_{participant}_trial_*.mat")):
                trial_number = int(path.stem.rsplit("_", 1)[1])
                if trial_number not in outcome_rows or trial_number not in windows:
                    raise ValueError(f"{path}: missing outcome or segmentation")
                trials.append(
                    load_trial_bytes(
                        path.read_bytes(), participant, trial_number, experiment,
                        outcome_rows[trial_number], windows[trial_number], accuracy_raw, segmentation_raw,
                    )
                )
                count += 1
        if count != EXPECTED[experiment]:
            raise ValueError(f"{experiment}: expected {EXPECTED[experiment]} trials, got {count}")
    if len(trials) != 1254:
        raise ValueError(f"expected 1254 PatCut trials, got {len(trials)}")
    return trials
