from pathlib import Path

from surgical_skill2.loaders.jigsaws import iter_trials


ROOT = Path(__file__).resolve().parent.parent


def test_authorized_jigsaws_copy_reconciles_and_is_valid():
    trials = iter_trials(ROOT / "data" / "raw" / "jigsaws")
    assert len(trials) == 103
    assert {trial.task for trial in trials} == {"Suturing", "Knot Tying", "Needle Passing"}
    assert len({trial.participant_source for trial in trials}) == 8
    assert all(6 <= trial.outcome_value <= 30 for trial in trials)

