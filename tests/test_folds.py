from surgical_skill2.folds import (
    held_out_participant_assignments,
    same_participant_assignments,
    validate_held_out,
    validate_same_participant,
)


def fixture_rows():
    return [
        {"dataset": "D", "task": "T", "participant_key": person, "trial_key": f"{person}{trial}", "repetition": trial}
        for person in ("a", "b", "c") for trial in range(1, 5)
    ]


def test_held_out_participant_is_grouped_and_deterministic():
    first = held_out_participant_assignments(fixture_rows())
    second = held_out_participant_assignments(fixture_rows())
    assert first == second
    validate_held_out(first)
    folds = {}
    for row in first:
        folds.setdefault(row["participant_key"], set()).add(row["test_fold"])
    assert all(len(value) == 1 for value in folds.values())


def test_same_participant_has_train_and_test_repetitions():
    assignments = same_participant_assignments(fixture_rows())
    validate_same_participant(assignments)
    folds = {}
    for row in assignments:
        folds.setdefault(row["participant_key"], set()).add(row["test_fold"])
    assert all(len(value) == 4 for value in folds.values())
    assert {row["test_fold"] for row in assignments if row["trial_key"].endswith("1")} == {"rep01"}
