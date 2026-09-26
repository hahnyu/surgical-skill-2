# Final locked analysis

Phase 5 locks the analysis to the exact Phase 3 and Phase 4 out-of-fold prediction artifacts. The single-command runner verifies their SHA-256 hashes before deriving any result, regenerates every table and SVG from source CSVs, and repeats the build to test byte-for-byte determinism.

## Locked primary decision

I4 adversarial suppression did not pass the prespecified two-probe verification rule, so I3 identity-subspace removal is the primary comparison with I0. I3 reduced both fresh identity probes:

- linear_probe: balanced-accuracy difference -0.184 (95% participant-bootstrap interval -0.215 to -0.151).
- nonlinear_probe: balanced-accuracy difference -0.138 (95% participant-bootstrap interval -0.175 to -0.098).

## New-user utility

Across the seven eligible dataset/task outcomes, the participant-average held-out-user I3 effect favored suppression in 1 and favored I0 in 6. Effects are reported task by task because the outcome scales and constructs differ; no pooled grand effect is estimated.

| Dataset/task | Standardized MAE difference | 95% participant-bootstrap interval |
|---|---:|---:|
| BGU-PatCut / Pattern Cutting | +0.029 | -0.038 to +0.091 |
| JIGSAWS / Knot Tying | +0.042 | -0.039 to +0.132 |
| JIGSAWS / Needle Passing | +0.125 | -0.018 to +0.290 |
| JIGSAWS / Suturing | -0.083 | -0.352 to +0.170 |
| ROSMA / Pea on a Peg | +24.141 | -0.019 to +72.407 |
| ROSMA / Post and Sleeve | +0.009 | -0.125 to +0.154 |
| ROSMA / Wire Chaser I | +0.004 | +0.000 to +0.011 |

Negative values favor I3. Standardization divides each paired trial-level absolute-error difference by the target SD calculated without that outer test fold.
ROSMA Pea on a Peg has a heavily zero-inflated error outcome; several outer-training SDs are small, so its standardized estimate and interval are correspondingly large. The raw-scale effect remains available in the Phase 4 tables, and the forest plots use an asinh display scale without changing source values.

## Protocol and permutation diagnostics

The ridge same-user versus held-out-user protocol gap was positive in 6 of 7 eligible tasks after fold-specific standardization. The JIGSAWS participant-wise label permutation remained substantially more favorable than record-wise permutation in all three tasks, consistent with identity-compatible same-user lookup.

## Mechanistic interpretation

The locked results support a narrow conclusion: participant identity is recoverable, targeted linear suppression reduces fresh-probe identity recovery, and that reduction does not consistently improve held-out-participant prediction. Most primary task intervals include zero, and JIGSAWS has only seven or eight participants per task; leave-one-participant results are therefore retained as a first-class sensitivity output.

## Reproduction

```bash
.venv/bin/python scripts/run_phase5_locked.py
```

The command validates Phases 1–4, rebuilds Phase 5 twice, compares output hashes, runs the complete test suite, and applies the Phase 5 acceptance validator.
