"""Deterministic trial and participant fold assignment."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256


def _stable(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def same_participant_assignments(rows: list[dict], n_splits: int = 5) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["dataset"], row["task"], row["participant_key"])].append(row)
    assignments = []
    for (dataset, task, participant), group in sorted(groups.items()):
        ordered = sorted(group, key=lambda row: (row.get("repetition") or -1, row["trial_key"]))
        repetitions = {row.get("repetition") for row in ordered}
        if None not in repetitions and len(repetitions) >= 2:
            # Preserve source-defined repetition/supertrial holdout across all
            # participants instead of rotating repetition labels by person.
            fold_for = lambda row: f"rep{int(row['repetition']):02d}"
        else:
            splits = min(n_splits, len(ordered))
            if splits < 2:
                raise ValueError(f"same-participant evaluation needs >=2 trials: {(dataset, task, participant)}")
            fold_for = lambda row: f"sp{int(_stable(row['trial_key'])[:8], 16) % splits:02d}"
        folds = {fold_for(row) for row in ordered}
        if len(folds) < 2:
            raise ValueError(f"same-participant evaluation needs >=2 trials: {(dataset, task, participant)}")
        for row in ordered:
            assignments.append(
                {
                    "dataset": dataset,
                    "task": task,
                    "protocol": "same_participant",
                    "test_fold": fold_for(row),
                    "trial_key": row["trial_key"],
                    "participant_key": participant,
                }
            )
    return sorted(assignments, key=lambda row: (row["dataset"], row["task"], row["test_fold"], row["trial_key"]))


def held_out_participant_assignments(rows: list[dict], large_dataset_splits: int = 10) -> list[dict[str, str]]:
    by_dataset: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_dataset[row["dataset"]].append(row)
    assignments = []
    for dataset, dataset_rows in sorted(by_dataset.items()):
        counts = Counter(row["participant_key"] for row in dataset_rows)
        participants = sorted(counts, key=lambda value: _stable(f"{dataset}\0{value}"))
        if len(participants) <= 18:
            fold_for = {participant: f"p{index:02d}" for index, participant in enumerate(participants)}
        else:
            fold_load = [0] * large_dataset_splits
            fold_for = {}
            for participant in sorted(participants, key=lambda value: (-counts[value], _stable(value))):
                fold = min(range(large_dataset_splits), key=lambda index: (fold_load[index], index))
                fold_for[participant] = f"gp{fold:02d}"
                fold_load[fold] += counts[participant]
        for row in dataset_rows:
            assignments.append(
                {
                    "dataset": dataset,
                    "task": row["task"],
                    "protocol": "held_out_participant",
                    "test_fold": fold_for[row["participant_key"]],
                    "trial_key": row["trial_key"],
                    "participant_key": row["participant_key"],
                }
            )
    return sorted(assignments, key=lambda row: (row["dataset"], row["task"], row["test_fold"], row["trial_key"]))


def validate_held_out(assignments: list[dict[str, str]]) -> None:
    participant_folds: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in assignments:
        participant_folds[(row["dataset"], row["participant_key"])].add(row["test_fold"])
    bad = {key: folds for key, folds in participant_folds.items() if len(folds) != 1}
    if bad:
        raise ValueError(f"participants assigned to multiple held-out folds: {bad}")
    for dataset in {row["dataset"] for row in assignments}:
        folds = {row["test_fold"] for row in assignments if row["dataset"] == dataset}
        for fold in folds:
            test_participants = {
                row["participant_key"] for row in assignments
                if row["dataset"] == dataset and row["test_fold"] == fold
            }
            train_participants = {
                row["participant_key"] for row in assignments
                if row["dataset"] == dataset and row["test_fold"] != fold
            }
            if test_participants & train_participants:
                raise ValueError(f"participant leakage in {dataset}/{fold}")


def validate_same_participant(assignments: list[dict[str, str]]) -> None:
    groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in assignments:
        groups[(row["dataset"], row["task"], row["participant_key"])].add(row["test_fold"])
    bad = {key: folds for key, folds in groups.items() if len(folds) < 2}
    if bad:
        raise ValueError(f"participants without both train and test trials: {bad}")
