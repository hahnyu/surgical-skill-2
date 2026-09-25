# Phase 4 identity-suppression interventions

Date: 2026-09-24  
Protocol: `protocol-v1`  
Configuration: [`phase4_interventions.yaml`](../configs/experiments/phase4_interventions.yaml)  
Status: **Phase 4 complete. The repository is stopped before Phase 5.**

## Gate result and primary decision

Phase 4 meets its acceptance criterion because I3 reduced both fresh identity
probes with participant-bootstrap intervals below zero. The comparison was
chosen using identity-probe results before task-performance effects: I4 was the
candidate primary intervention, but it failed the nonlinear-probe verification,
so the frozen fallback rule designated `I3_identity_subspace` versus
`I0_unsuppressed` as primary.

| Candidate versus control | Linear balanced-accuracy difference [95% CI] | Nonlinear difference [95% CI] | Verified on both probes | Primary |
|---|---:|---:|:---:|:---:|
| I3 versus I0 | −0.184 [−0.215, −0.151] | −0.138 [−0.175, −0.098] | Yes | Yes |
| I4 versus capacity-matched λ=0 | −0.048 [−0.082, −0.015] | −0.003 [−0.038, +0.032] | No | No |

Each estimate averages dataset/task groups equally; I4 also averages its three
seeds. The intervals resample participants within each group. Because each
identity class is one participant, participant-average accuracy is balanced
accuracy. Fresh probes were trained after the representation was frozen and did
not reuse the I3 identity classifier or I4 adversary.

## Primary held-out-participant task result

Negative values favor I3. Intervals resample participants and remain in each
dataset's native outcome units, so effects are presented task by task rather
than pooled across incompatible scales.

| Dataset/task | I3 minus I0 participant-average MAE [95% CI] |
|---|---:|
| BGU-PatCut / Pattern Cutting | +487.183 [−648.849, +1,613.362] |
| JIGSAWS / Knot Tying | +0.205 [−0.195, +0.604] |
| JIGSAWS / Needle Passing | +0.618 [−0.045, +1.400] |
| JIGSAWS / Suturing | −0.401 [−1.757, +0.938] |
| ROSMA / Pea on a Peg | +28.858 [−0.020, +86.539] |
| ROSMA / Post and Sleeve | +0.005 [−0.072, +0.086] |
| ROSMA / Wire Chaser I | +0.003 [0.000, +0.008] |

I3 improved one of seven held-out task estimates and harmed six; all but wire
chasing had intervals spanning zero. Identity suppression therefore succeeded
technically but did not improve unseen-user prediction overall. The large and
uncertain pea-on-a-peg effect retains the previously documented finite source
spikes in `X01_Pea_on_a_Peg_03`; no post-result exclusion was made.

## Ablations and falsification controls

Direct duration removal did not suppress identity: its mean linear and
nonlinear probe differences versus I0 were +0.018 and +0.002. Duration
residualization changed them by +0.013 and −0.025. The I3-matched random
projection changed identity scores by −0.018 and +0.011 versus I0 and was worse
than I3 by +0.167 and +0.149. This supports removal of learned identity
directions rather than generic dimensionality reduction as the source of I3's
probe reduction.

I4's shuffled-identity-head control changed linear and nonlinear scores by
−0.039 and +0.019 versus the λ=0 network. I4's real identity head reduced the
linear score more consistently, but its nonlinear difference was close to zero.
The gradient-reversal mechanism therefore did not receive a verified I4 claim.

Fold-local I3 selection chose a positive `k` in 112 of 144 outer folds. Values
not literally listed in the grid arise when a grid value is clipped to the
training fold's maximum identity rank. I4 chose a nonzero λ in 116 of 126 folds:
λ=0.01 twice, 0.1 fourteen times, 0.3 forty-six times, and 1.0 fifty-four times.
Ten folds retained λ=0 under the frozen utility rule.

## JIGSAWS person-level skill endpoint

The designated I3 intervention did not uniformly reduce same-participant skill
accuracy. Participant-average accuracy changed by −0.025 for knot tying, 0.000
for needle passing, and +0.025 for suturing. The corresponding intervals were
[−0.075, 0.000], [0.000, 0.000], and [−0.100, +0.125]. Thus H6 was not supported
as a consistent task-level effect even though I3 measurably removed recoverable
identity information.

Across I4 seeds, skill-accuracy ranges were at most 0.179. Identity-probe seed
ranges had a median of 0.072 and maximum of 0.225. Task-MAE seed ranges are
reported per dataset/task in `phase4_seed_stability.csv`; their raw maximum is
dominated by native-scale PatCut and the retained ROSMA pea-on-a-peg anomaly.

## Leakage controls and reproducibility

- Imputation, scaling, duration regression, identity bases, random projections,
  network encoders, task heads, and probe tuning use outer-training rows only.
- I3 `k` and I4 λ are selected only from nested inner splits. The outer test
  fold is applied after the transformation is fixed.
- The λ=0 network uses the same architecture, initialization, and training order
  as I4. The shuffled identity head and matched random projection provide the
  prespecified negative controls.
- All 19 unit tests pass, including gradient sign, fixed-seed reproducibility,
  and an explicit test that outer-test perturbation cannot alter the I3 basis.
- Private out-of-fold artifacts remain Git-ignored. Their 98,620 rows, hashes,
  configuration hash, and generating commits are recorded in
  [`phase4_artifacts.csv`](../data/manifests/phase4_artifacts.csv).
- Aggregate task, identity, skill, selection, stability, primary-decision, and
  ablation tables are committed under `results/metrics/`.

I5 was optional and was not run. Phase 5 manuscript synthesis and robustness
work have not begun.
