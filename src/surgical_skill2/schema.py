"""Dataset-neutral trial objects used by every Phase 2 loader."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import numpy as np


def public_key(dataset: str, source_id: str, length: int = 16) -> str:
    """Return a stable opaque key without exposing a source participant/file ID."""
    return sha256(f"protocol-v1\0{dataset}\0{source_id}".encode()).hexdigest()[:length]


@dataclass(frozen=True)
class ArmSeries:
    """One instrument's positions and optional gripper/jaw on its own clock."""

    timestamps_s: np.ndarray
    position_m: np.ndarray
    gripper: np.ndarray | None = None

    def validate(self) -> None:
        t = np.asarray(self.timestamps_s, dtype=np.float64)
        p = np.asarray(self.position_m, dtype=np.float64)
        if t.ndim != 1 or p.ndim != 2 or p.shape[1] != 3 or len(t) != len(p):
            raise ValueError("arm series must have timestamps (n,) and positions (n, 3)")
        if len(t) < 4:
            raise ValueError("arm series must contain at least four samples")
        if not np.isfinite(t).all() or not np.isfinite(p).all():
            raise ValueError("arm series contains non-finite timestamps or positions")
        if np.any(np.diff(t) <= 0):
            raise ValueError("arm timestamps must be strictly increasing")
        if self.gripper is not None:
            g = np.asarray(self.gripper, dtype=np.float64)
            if g.ndim != 1 or len(g) != len(t) or not np.isfinite(g).all():
                raise ValueError("gripper must be a finite vector aligned to positions")


@dataclass(frozen=True)
class Trial:
    """A complete, task-windowed trial in the common schema."""

    dataset: str
    version: str
    task: str
    participant_source: str
    trial_source: str
    repetition: int | None
    session: str | None
    condition: str | None
    outcome_name: str | None
    outcome_value: float | None
    outcome_direction: str | None
    task_duration_s: float
    psm1: ArmSeries
    psm2: ArmSeries
    source_sha256: str

    @property
    def participant_key(self) -> str:
        return public_key(self.dataset, self.participant_source)

    @property
    def trial_key(self) -> str:
        return public_key(self.dataset, self.trial_source)

    def validate(self) -> None:
        if not self.dataset or not self.task or not self.participant_source or not self.trial_source:
            raise ValueError("dataset, task, participant, and trial identifiers are required")
        if self.outcome_name is None and self.outcome_value is not None:
            raise ValueError("an outcome value requires an outcome name")
        if self.outcome_direction not in {None, "higher_better", "lower_better"}:
            raise ValueError("invalid outcome direction")
        if not np.isfinite(self.task_duration_s) or self.task_duration_s <= 0:
            raise ValueError("task_duration_s must be finite and positive")
        if len(self.source_sha256) != 64:
            raise ValueError("source_sha256 must be a SHA-256 hex digest")
        self.psm1.validate()
        self.psm2.validate()
