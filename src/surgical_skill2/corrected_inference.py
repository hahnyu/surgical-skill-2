"""Post-lock inference corrections; independent of the frozen analysis runners.

Inference conditions on existing out-of-fold predictions, not on refitted models.
"""
from collections import Counter, defaultdict
import math
import random


def percentile(values, probability):
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (index - lower) * (ordered[upper] - ordered[lower])


def cluster_identity_effect(rows, replicates=2000, seed=20261116):
    """Average seeds first; resample people jointly across tasks within dataset.

    Every dataset-task has equal weight. Missing tasks stay missing. A draw
    containing no observed person in a task is rejected in its entirety.
    Repeated seeds are not independent sampling units.
    """
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for row in rows:
        values = grouped[row['dataset']][row['task']][row['participant_key']]
        seed_key = str(row.get('seed', 'single'))
        if seed_key in values:
            raise ValueError('Duplicate participant/task/seed effect')
        value = float(row['value'])
        if not math.isfinite(value):
            raise ValueError('Non-finite effect')
        values[seed_key] = value
    if not grouped or replicates < 2:
        raise ValueError('Need observations and at least two replicates')
    maps = {
        dataset: {task: {p: sum(v.values()) / len(v) for p, v in sorted(people.items())}
                  for task, people in sorted(tasks.items())}
        for dataset, tasks in sorted(grouped.items())
    }
    population = {d: sorted({p for ps in tasks.values() for p in ps}) for d, tasks in maps.items()}
    task_count = sum(len(tasks) for tasks in maps.values())
    estimate = sum(sum(ps.values()) / len(ps) for tasks in maps.values() for ps in tasks.values()) / task_count
    rng = random.Random(seed)
    draws = []
    attempts = 0
    while len(draws) < replicates:
        attempts += 1
        if attempts > replicates * 100:
            raise ValueError('Too many draws with empty task support')
        means = []
        for dataset, tasks in maps.items():
            counts = Counter(rng.choices(population[dataset], k=len(population[dataset])))
            for people in tasks.values():
                denominator = sum(counts[p] for p in people)
                if denominator:
                    means.append(sum(v * counts[p] for p, v in people.items()) / denominator)
        if len(means) == task_count:
            draws.append(sum(means) / task_count)
    return dict(estimate=estimate, ci_low=percentile(draws, .025),
                ci_high=percentile(draws, .975), replicates=replicates,
                tasks=task_count, participants=sum(map(len, population.values())),
                rejected_draws=attempts-replicates), draws


def matched_permutation_p(observed, null, *, observed_spec, null_spec):
    """Refuse comparisons across model, preprocessing or selection pipelines."""
    if observed_spec != null_spec:
        raise ValueError('Observed and null pipelines do not match')
    if not null or not all(math.isfinite(float(v)) for v in [observed, *null]):
        raise ValueError('Need finite observed and null statistics')
    return (1 + sum(v >= observed for v in null)) / (1 + len(null))
