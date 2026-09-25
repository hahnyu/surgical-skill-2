# Phase 3 baseline replication and identity audit

Date: 2026-09-24  
Protocol: `protocol-v1`  
Analysis commit recorded in every prediction: `1008ee2`  
Configuration: [`phase3_baseline.yaml`](../configs/experiments/phase3_baseline.yaml)  
Status: **Phase 3 complete. No identity-suppression intervention was fitted.**

## Gate result

Phase 3 meets its acceptance criteria. All metrics below were regenerated from
saved out-of-fold prediction artifacts. The private artifacts contain opaque
trial and participant keys and remain Git-ignored because JIGSAWS is access
controlled; [`phase3_artifacts.csv`](../data/manifests/phase3_artifacts.csv)
commits their row counts and SHA-256 hashes.

- Feature-free mean/median, duration-only, and unsuppressed models ran under
  both same-participant and held-out-participant protocols.
- Fresh linear and nonlinear identity probes ran on every dataset/task.
- Each JIGSAWS task used 200 paired participant-wise and record-wise label
  permutations.
- Fifty record-wise identity-label and continuous-outcome permutations per
  dataset/task supplied negative controls.
- The leakage canary was detected, excluded from production predictors, and
  yielded 100% identity accuracy when intentionally exposed.
- Eleven of twelve paper-1 endpoints reproduced within the frozen tolerances;
  the remaining discrepancy is explained below.

## JIGSAWS protocol gap

The same-participant skill classifier again appeared much stronger than the
held-out-participant classifier.

| Task | Same-participant accuracy | Held-out-participant accuracy | Participant-averaged gap [95% CI] |
|---|---:|---:|---:|
| Knot Tying | 0.917 | 0.444 | +0.419 [0.063, 0.775] |
| Needle Passing | 1.000 | 0.464 | +0.479 [0.214, 0.757] |
| Suturing | 0.872 | 0.462 | +0.400 [0.150, 0.675] |

The fold-only participant lookup achieved 1.000 accuracy for all three tasks
under the same-participant protocol. This is a positive control demonstrating
that person-constant skill labels are structurally retrievable when the person
has training records; it is not a deployable model.

For GRS ridge regression, held-out-participant minus same-participant MAE was
+0.770 for knot tying, +0.174 for needle passing, and +1.722 for suturing. The
participant-bootstrap interval excluded zero only for suturing (+0.204 to
+3.413). The classification gap is therefore the clearer paper-1 replication.

## Feature-free, duration-only, and unsuppressed regression

| Dataset/task | Protocol | Mean reference MAE | Duration-only MAE | Unsuppressed ridge MAE |
|---|---|---:|---:|---:|
| JIGSAWS / Knot Tying | same | 4.663 | 2.845 | 2.618 |
| JIGSAWS / Knot Tying | held participant | 5.100 | 3.217 | 3.385 |
| JIGSAWS / Needle Passing | same | 4.218 | 4.332 | 2.908 |
| JIGSAWS / Needle Passing | held participant | 4.410 | 4.675 | 3.063 |
| JIGSAWS / Suturing | same | 4.351 | 4.250 | 3.244 |
| JIGSAWS / Suturing | held participant | 4.714 | 4.903 | 4.989 |
| ROSMA / Pea on a Peg | same | 0.830 | 0.839 | 21.400 |
| ROSMA / Pea on a Peg | held participant | 0.848 | 0.864 | 6.547 |
| ROSMA / Post and Sleeve | same | 0.437 | 0.453 | 0.434 |
| ROSMA / Post and Sleeve | held participant | 0.445 | 0.449 | 0.444 |
| ROSMA / Wire Chaser I | same | 0.520 | 0.494 | 0.439 |
| ROSMA / Wire Chaser I | held participant | 0.541 | 0.534 | 0.507 |
| BGU-PatCut / Pattern Cutting | same | 12,275 | 12,273 | 9,284 |
| BGU-PatCut / Pattern Cutting | held participant | 12,369 | 12,377 | 10,512 |

The PatCut error scale is dataset native and must not be compared numerically
with GRS or ROSMA error counts. Under held-out participants, the harmonized
ridge improved over the mean reference on knot tying, needle passing, wire
chasing, and PatCut; it did not improve suturing, ROSMA pea-on-a-peg, or
post-and-sleeve. Phase 3 estimates baselines and does not select tasks or alter
the prospective Phase 4 endpoint hierarchy.

### ROSMA finite source spikes

The poor pea-on-a-peg ridge result is driven by one retained trial,
`X01_Pea_on_a_Peg_03`. Its deposited PSM2 x-coordinate contains isolated
finite values `69.0` and `86.0` between observations near `0.069` and `0.086`
metres. Because these are finite rather than missing, the Phase 2 gap rule does
not remove them. The same-participant ridge predicts 1,463 for this trial and
the held-out-participant ridge predicts 408, while the observed error count is
1. Removing or correcting this record after seeing its model effect would be a
post-result outlier exclusion forbidden by §7.6, so the primary Phase 3 result
retains it. A future sensitivity analysis may be labelled post hoc, but cannot
replace this result.

## Identity recoverability

Every unsuppressed linear and nonlinear probe exceeded its 50-permutation
record-wise identity null (`p=0.0196`, the attainable Monte Carlo floor).

| Dataset/task | Linear balanced accuracy | Nonlinear balanced accuracy | Shuffled-label median |
|---|---:|---:|---:|
| JIGSAWS / Knot Tying | 0.869 | 0.827 | 0.084 |
| JIGSAWS / Needle Passing | 0.943 | 0.840 | 0.064 |
| JIGSAWS / Suturing | 0.944 | 0.844 | 0.075 |
| ROSMA / Pea on a Peg | 0.381 | 0.397 | 0.056 |
| ROSMA / Post and Sleeve | 0.446 | 0.381 | 0.062 |
| ROSMA / Wire Chaser I | 0.228 | 0.431 | 0.060 |
| BGU-SKILLS / Knot Tying | 0.530 | 0.393 | 0.051 |
| BGU-SKILLS / Ring Tower Transfer | 0.596 | 0.487 | 0.050 |
| BGU-SKILLS / Suturing | 0.762 | 0.618 | 0.049 |
| BGU-PatCut / Pattern Cutting | 0.834 | 0.750 | 0.016 |

Duration-only balanced accuracy was low (0.056–0.225). It did not account for
the strong identity signal in the full representation. These probes show that
identity-compatible information is available; they do not by themselves show
that an outcome model used it.

## Formal identity-confounding permutation test

| JIGSAWS task | Observed | Participant-wise median [95% range] | Record-wise median [95% range] | Median paired difference | Empirical p |
|---|---:|---:|---:|---:|---:|
| Knot Tying | 0.917 | 0.778 [0.610, 0.917] | 0.306 [0.167, 0.501] | +0.444 | 0.004975 |
| Needle Passing | 0.964 | 0.875 [0.750, 1.000] | 0.321 [0.143, 0.501] | +0.536 | 0.004975 |
| Suturing | 0.872 | 0.923 [0.846, 0.974] | 0.359 [0.179, 0.538] | +0.538 | 0.004975 |

Participant-wise permutation destroys the original skill assignment but keeps
one label per participant. Its high accuracy, compared with freely permuted
trial labels, confirms that the same-participant pipeline can exploit
participant-compatible structure when the target is constant within person.

Grouped permutations were not applied mechanically to GRS, ROSMA errors, or
PatCut total error because those outcomes vary within participant and grouped
exchangeability was not established. Their required record-wise negative
controls behaved as expected: the median ridge improvement over the fold mean
was negative for all seven dataset/task outcomes (from -0.043 to -216 in their
native scales).

## Paper-1 replication

All six JIGSAWS skill-accuracy endpoints were within the predeclared absolute
tolerance of 0.15. Five of six GRS MAEs were within 1.0 point. Held-out-person
needle-passing MAE was 3.063 here versus 4.910 in paper 1, an absolute
difference of **1.8467** points.

This discrepancy is favorable but not a literal reproduction failure hidden by
selective reporting. Phase 3 uses the new 41-variable harmonized feature set,
task transcription windows, exact repetition folds, fold-specific imputation
and scaling, and nested alpha selection. Paper 1 used its earlier 16-feature
5 Hz representation and pipeline. The other eleven endpoints remaining within
tolerance, plus close identity and permutation findings, support replication of
the central protocol/identity result while showing that needle-passing GRS
regression is representation sensitive.

## Reproducibility and controls

- `results/metrics/phase3_performance.csv` and
  `phase3_protocol_gap.csv` contain the task metrics and paired gaps.
- `phase3_identity_probes.csv` contains both probes and their empirical null.
- `phase3_skill_permutation_summary.csv` and the corresponding distribution
  table contain all 200 paired tests.
- `phase3_paper1_replication.csv` records every expected value, observed value,
  tolerance, and pass/fail decision.
- [`phase3_leakage_canary.json`](../results/metrics/phase3_leakage_canary.json)
  records successful identifier detection and the isolated one-hot positive
  control.
- Thirteen unit tests cover deterministic features/folds, held-out inner
  splits, training-only scaling, canary rejection, fixed-seed nonlinear
  predictions, and the authorized JIGSAWS cohort.
