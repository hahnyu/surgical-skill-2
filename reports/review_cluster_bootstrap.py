"""Review-only sensitivity; does not overwrite the locked analysis.

Run with Python 3 from any directory. Resample dataset-participants jointly
across tasks after averaging seeds within participant/task. Preserve equal task
weights. This conditions on saved out-of-fold predictions, without refitting.
"""
import collections
import csv
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader((ROOT / 'results/locked/phase5_participant_identity_effects.csv').open()))
output = []
for candidate, baseline in [('I3_identity_subspace', 'I0_unsuppressed'), ('I4_adversarial', 'I4_capacity_lambda0')]:
    for model in ['linear_probe', 'nonlinear_probe']:
        groups = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
        for row in rows:
            if (row['candidate'], row['baseline'], row['model']) == (candidate, baseline, model):
                groups[row['dataset']][row['task']][row['participant_key']].append(float(row['value']))
        maps = {d: {t: {p: sum(v)/len(v) for p, v in ps.items()} for t, ps in ts.items()} for d, ts in groups.items()}
        people = {d: sorted({p for ps in ts.values() for p in ps}) for d, ts in maps.items()}
        point = sum(sum(ps.values())/len(ps) for ts in maps.values() for ps in ts.values()) / sum(len(ts) for ts in maps.values())
        rng = random.Random(20261116)
        bootstrap = []
        while len(bootstrap) < 2000:
            means = []
            valid = True
            for dataset, tasks in maps.items():
                counts = collections.Counter(rng.choices(people[dataset], k=len(people[dataset])))
                for participants in tasks.values():
                    denominator = sum(counts[p] for p in participants)
                    if not denominator:
                        valid = False
                        break
                    means.append(sum(v*counts[p] for p, v in participants.items())/denominator)
            if valid:
                bootstrap.append(sum(means)/len(means))
        bootstrap.sort()
        output.append(dict(candidate=candidate, model=model, estimate=point,
                           ci_low=bootstrap[49], ci_high=bootstrap[1949], replicates=2000,
                           note='Review-only cluster bootstrap; order-statistic percentile endpoints; no model refits'))
print(json.dumps(output, indent=2))
