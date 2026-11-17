import pytest
from surgical_skill2.corrected_inference import cluster_identity_effect, matched_permutation_p


def effects(tasks=('A',), seeds=(1,)):
    return [dict(dataset='D', task=t, participant_key=p, seed=s, value=v)
            for t in tasks for s in seeds for p, v in [('p1', -1), ('p2', 1), ('p3', 3)]]


def test_repeating_correlated_tasks_and_seeds_does_not_shrink_uncertainty():
    single, draws = cluster_identity_effect(effects(), replicates=100, seed=1)
    repeated, repeated_draws = cluster_identity_effect(effects(('A', 'B'), (1, 2, 3)), replicates=100, seed=1)
    assert draws == repeated_draws
    assert single['ci_low'] == repeated['ci_low']
    assert single['estimate'] == repeated['estimate'] == 1
    assert repeated['participants'] == 3


def test_equal_task_weight_with_missing_participant_and_deterministic_order():
    rows = effects() + [dict(dataset='D', task='B', participant_key='p1', seed=1, value=9)]
    result, draws = cluster_identity_effect(rows, 100, 1)
    reverse, reversed_draws = cluster_identity_effect(list(reversed(rows)), 100, 1)
    assert result == reverse and draws == reversed_draws
    assert result['estimate'] == 5
    assert result['rejected_draws'] > 0


def test_permutation_test_rejects_unmatched_pipelines():
    with pytest.raises(ValueError, match='do not match'):
        matched_permutation_p(.9, [.1, .2], observed_spec='tuned', null_spec='fixed_C1')
    assert matched_permutation_p(.9, [.1] * 50, observed_spec='fixed_C1', null_spec='fixed_C1') == 1/51
