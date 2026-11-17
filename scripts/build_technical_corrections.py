#!/usr/bin/env python3
"""Dated post-lock correction. Never overwrites the Phase 3--5 artifacts.

No models are refitted. Unmatched identity tests and the inferential label on
the two-scheme skill shuffle comparison are withdrawn.
"""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from surgical_skill2.corrected_inference import cluster_identity_effect, matched_permutation_p

OUT = ROOT / 'results' / 'corrections' / '2026-11-16'


def read(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def write(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'results/locked/phase5_participant_identity_effects.csv'
    rows = read(source)
    summaries, draws = [], []
    pairs = sorted({(r['candidate'], r['baseline'], r['model']) for r in rows})
    for candidate, baseline, model in pairs:
        selected = [r for r in rows if (r['candidate'], r['baseline'], r['model']) == (candidate, baseline, model)]
        result, bootstrap = cluster_identity_effect(selected)
        summaries.append(dict(candidate=candidate, baseline=baseline, model=model, **result,
                              probe_endpoint_passed=result['ci_high'] < 0))
        draws.extend(dict(candidate=candidate, baseline=baseline, model=model, replicate=i, value=v)
                     for i, v in enumerate(bootstrap))
    write(OUT / 'identity_cluster_effects.csv', summaries)
    write(OUT / 'identity_cluster_bootstrap.csv', draws)
    print('Joint participant bootstrap complete', flush=True)

    identity_path = ROOT / 'results/metrics/phase3_identity_probes.csv'
    identity = read(identity_path)
    descriptive = [{k: r[k] for k in ['dataset', 'task', 'model', 'participants', 'balanced_accuracy',
                                      'balanced_accuracy_ci_low', 'balanced_accuracy_ci_high']}
                   for r in identity]
    write(OUT / 'identity_descriptive.csv', descriptive)
    distribution_path = ROOT / 'results/metrics/phase3_skill_permutation_distribution.csv'
    distribution = read(distribution_path)
    from statistics import median
    skill = []
    for task in sorted({r['task'] for r in distribution}):
        participant = {r['permutation']: float(r['accuracy']) for r in distribution
                       if r['task'] == task and r['permutation_type'] == 'participant_wise'}
        record = {r['permutation']: float(r['accuracy']) for r in distribution
                  if r['task'] == task and r['permutation_type'] == 'record_wise'}
        if participant.keys() != record.keys() or len(participant) != 200:
            raise ValueError('Skill shuffle pairs are incomplete')
        differences = [participant[k] - record[k] for k in sorted(participant)]
        skill.append(dict(task=task, median_difference=median(differences),
                          nonpositive_pairs=sum(v <= 0 for v in differences), paired_draws=len(differences),
                          interpretation='descriptive Monte Carlo comparison; not a hypothesis-test p-value'))
    write(OUT / 'skill_permutation_diagnostics.csv', skill)
    inputs = [source, identity_path, distribution_path,
              ROOT / 'scripts/build_technical_corrections.py',
              ROOT / 'src/surgical_skill2/corrected_inference.py']
    manifest = dict(date='2026-11-16', status='post-lock correction',
                    bootstrap_seed=20261116, bootstrap_replicates=2000,
                    percentile='linear interpolation at .025 and .975',
                    identity_tests='withdrawn: fixed-C null does not match tuned observed models',
                    skill_tests='descriptive shuffling comparison, not a hypothesis test',
                    inputs={str(p.relative_to(ROOT)): digest(p) for p in inputs},
                    outputs={str(p.relative_to(ROOT)): digest(p) for p in sorted(OUT.glob('*.csv'))})
    (OUT / 'analysis_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
