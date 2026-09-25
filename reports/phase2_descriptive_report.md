# Phase 2 harmonized preprocessing report

Date: 2026-09-21  
Protocol: `protocol-v1`  
Status: **Phase 2 complete; no predictive model trained**

## Gate result

The deterministic loaders produced 2,501 complete task trials from four
datasets. Two independent extractions produced the identical private feature
file SHA-256:

```text
0c351007805f52f41459f622faa3c979f0b410685006763fbfcba1fc431a1e50
```

Both committed fold manifests contain 2,501 unique opaque trial keys. The
held-out-participant validator confirmed that each participant appears in one
test fold per dataset and that no participant is shared between training and
test partitions. Phase 2 therefore meets all acceptance criteria in the
prospective master specification.

## Reconciled cohort

| Dataset | Task | Participants | Included trials | Median duration (s) | Median sampling (Hz) | Outcome |
|---|---|---:|---:|---:|---:|---|
| JIGSAWS | Knot Tying | 8 | 36 | 43.53 | 30.00 | GRS, 6–22 |
| JIGSAWS | Needle Passing | 7 | 28 | 106.95 | 30.00 | GRS, 7–24 |
| JIGSAWS | Suturing | 8 | 39 | 101.60 | 30.00 | GRS, 8–30 |
| ROSMA | Pea on a Peg | 12 | 71 | 127.81 | 50.00 | errors, 0–7 |
| ROSMA | Post and Sleeve | 12 | 65 | 121.98 | 50.00 | errors, 0–2 |
| ROSMA | Wire Chaser I | 12 | 70 | 30.93 | 50.00 | errors, 0–4 |
| BGU-SKILLS | Knot Tying | 18 | 311 | 114.59 | 50.00 | none |
| BGU-SKILLS | Ring Tower Transfer | 18 | 312 | 81.55 | 50.00 | none |
| BGU-SKILLS | Suturing | 18 | 315 | 274.63 | 50.00 | none |
| BGU-PatCut | Pattern Cutting | 54 | 1,254 | 94.51 | 99.14 | total scan error, 1–121,646 |

The counts reconcile to the source-defined cohorts: JIGSAWS 103, ROSMA 206,
BGU-SKILLS 938, and BGU-PatCut 1,254. BGU-SKILLS deposits 972 raw kinematic
members (324 per task); the source notes retain 311, 312, and 315 trials,
respectively. The analysis follows those inclusion flags rather than silently
promoting excluded recordings.

The machine-readable task table is
[`tables/phase2_dataset_descriptives.csv`](tables/phase2_dataset_descriptives.csv).

## Common trial schema and task windows

Every loader emits one `Trial` with dataset/version, task, source participant
and trial identifiers, repetition/session/condition, outcome provenance,
task duration, two timestamped instrument position streams, optional gripper
signals, and a hash of the source bytes. Source identifiers are used only in
memory; committed artifacts use stable 16-character SHA-256-derived keys.

- **JIGSAWS:** the task window runs from the first transcription start frame to
  the final transcription end frame at 30 Hz. The loader requires 76 kinematic
  columns and verifies that GRS equals the sum of its six elements.
- **ROSMA:** timestamps are parsed from the `Date` field, non-finite position
  rows and duplicate/backward times are removed, and the independently
  observed error count is joined by exact filename.
- **BGU-SKILLS:** the window runs from the first `Start Task` to the final
  `Finish Task`; only trials marked included in the source notes enter the
  cohort. Non-finite robot rows are removed without closing their time gaps.
- **BGU-PatCut:** each arm is trimmed to its single segmentation `StartTime` and
  `FinishTime`; jaw samples are aligned to position timestamps. The loader
  verifies `TotalErrors = TotalErrorsInside + TotalErrorsOutside` for every
  participant before emitting trials.

## Fixed feature extraction

The same position-based summaries are computed for each arm: sample rate,
path length, speed mean/standard deviation/10th/50th/90th quantiles, absolute
acceleration mean/90th quantile, absolute jerk mean/90th quantile, idle
fraction at 0.001 m/s, workspace bounding-box volume, and recording-gap
fraction. Where available, gripper mean, standard deviation, range, and total
variation are added. Bimanual features are aligned speed correlation and path
length asymmetry.

Steps spanning more than three times an arm's median interval are excluded
from path and derivative calculations. Interpolated points more than 2.5
nominal samples from a real observation are excluded from bimanual
correlation. This prevents missing blocks from becoming artificial motion.
There are 113 BGU-SKILLS trials and 119 ROSMA trials with a nonzero gap field;
JIGSAWS and BGU-PatCut have none under this rule. The decision is recorded in
[`docs/DEVIATIONS.md`](../docs/DEVIATIONS.md) because it was added after direct
source inspection and before modeling.

## Fold manifests

[`same_participant.csv`](../data/folds/same_participant.csv) assigns trials by
their source-defined repetition/supertrial: 5 folds for JIGSAWS, 6 for ROSMA
and BGU-SKILLS, and 24 for BGU-PatCut. Every participant-task group occupies at
least two folds. This exact repetition mapping was corrected before the first
Phase 3 model run; the earlier participant-rotated draft was never used for a
prediction.

[`held_out_participant.csv`](../data/folds/held_out_participant.csv) uses one
fold per participant for JIGSAWS (8 folds), ROSMA (12), and BGU-SKILLS (18).
BGU-PatCut uses 10 participant-group folds balanced by trial count. Participant
membership is indivisible across all tasks and trials.

| Artifact | Rows | SHA-256 |
|---|---:|---|
| Private harmonized features | 2,501 | `0c351007805f52f41459f622faa3c979f0b410685006763fbfcba1fc431a1e50` |
| Same-participant folds | 2,501 | `f3fb5ad3e7345f4be8f2e1dbbf9a182a7afe592e14ce7ccd73200bf0093a46f2` |
| Held-out-participant folds | 2,501 | `38be25e0374f77d764e83c8c295e5d6f25611db8ab2e9e6077debea904e3a978` |

The private matrix is intentionally ignored because redistribution terms differ
by source. Its schema, extraction code, hash, aggregate table, and opaque fold
assignments are committed so an authorized user can reproduce it exactly.

## Validation performed

- Two end-to-end extractions from raw inputs produced identical bytes.
- Loader assertions reconciled every task and dataset count.
- Unit tests checked exact features on a known trajectory, deterministic
  output, discontinuity handling, stable folds, participant isolation, and the
  authorized JIGSAWS cohort.
- The Phase 2 validator checked 2,501 unique trials, expected participant/task
  counts, finite core features, fold coverage, held-out leakage, artifact
  hashes, and the independent rerun hash.
- The Phase 1 validation gate was retained; Phase 2 does not revise target
  eligibility or outcome interpretation.
