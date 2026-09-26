---
title: "Supplement: Operator identity and out-of-user generalization in automated surgical skill assessment"
bibliography: references.bib
date: 2026-09-26
---

# S1. Purpose and locked analysis boundary

This supplement documents the study population, outcome provenance, preprocessing, folds, models, interventions, inference, robustness analyses, deviations, and reproducibility controls. It accompanies the Phase 5 locked outputs. No model was refit for manuscript preparation. The exact private out-of-fold inputs were verified against `data/manifests/phase3_artifacts.csv` and `data/manifests/phase4_artifacts.csv`; Phase 5 derived all inferential summaries from those files.

The protocol was frozen as Git tag `protocol-v1` on 21 September 2026. The Phase 5 artifact manifest is `data/manifests/phase5_artifacts.csv`, whose locked manifest SHA-256 is `a4345fc8cdcb50b90e286914ff6dec8ec1c7373e248f60a260c4eaf11f0d9bc3`.

# S2. Dataset acquisition, licenses, and cohorts

## S2.1 JIGSAWS

The JHU-ISI Gesture and Skill Assessment Working Set contains synchronized kinematics, video, task transcriptions, modified-OSATS ratings, and self-declared experience groups [@Ahmidi2017]. Access is governed by an academic research agreement. An authorized local copy was connected by a Git-ignored symbolic link; raw or participant-level derived records were not committed. We used 36 knot-tying, 28 needle-passing, and 39 suturing trials after exact matching of kinematics, transcriptions, and ratings. Needle passing represented seven participants; the other tasks represented eight.

Total GRS was verified as the sum of six rating elements for every included trial. The novice/intermediate/expert label was treated as person-constant and was not represented as a trial-varying expert judgment.

## S2.2 ROSMA

ROSMA version `10.5281/zenodo.7100542` is distributed under CC BY 4.0 and contains kinematics and task scoring for 12 participants [@RivasBlanco2023; @ROSMAData2022]. Exact kinematic-score matching yielded 71 pea-on-a-peg, 65 post-and-sleeve, and 70 wire-chaser-I trials. The deposited score table had one additional wire-chaser target without matching kinematics. Observed task errors were retained. Completion time and the composite source score were excluded because their formulas use duration, which is directly represented in the inputs.

Errors were zero inflated: 30/71 pea-on-a-peg, 14/65 post-and-sleeve, and 17/70 wire-chaser trials had nonzero errors. A deposited pea-on-a-peg record contained isolated finite coordinate spikes. They were retained because the protocol prohibited discretionary post-result exclusion.

## S2.3 BGU-SKILLS

BGU-SKILLS version 1.0 (`10.17617/3.CYSIAP`) is distributed under CC BY 4.0 [@Sharon2025; @BGUSkillsData2025]. The study enrolled 21 residents and reported three withdrawals, leaving 18 participants and 972 scheduled trials. We followed the source inclusion notes, retaining 311 knot-tying, 312 ring-transfer, and 315 suturing trials (938 total). Completion time, path length, and orientation-change rate are direct functions of kinematics and were ineligible as independent outcomes. The dataset therefore contributed to identity recovery and longitudinal robustness only.

## S2.4 BGU-PatCut

BGU-PatCut version 2.1 (`10.17617/3.JK4ANF`) is distributed under CC BY 4.0 [@SharonPatCut2024; @PatCutData2024]. The cohort comprised 30 force-perturbation and 24 motion-perturbation participants, each scheduled for 24 trials. Source missing-trial lists yielded 700 and 554 available trials, respectively. Total cutting error (`TE = Eoutside + Einside`) was verified for each participant and retained because it was measured from an independent post-trial gauze image. Task time and the composite efficiency score were excluded because they contain duration.

## S2.5 Cohort summary

| Dataset | Tasks | Trials | Participants | Performance-analysis role |
|---|---|---:|---:|---|
| JIGSAWS | Knot tying; needle passing; suturing | 103 | 8 overall | Expert-rated GRS; person-level mechanism |
| ROSMA | Pea on a peg; post and sleeve; wire chaser I | 206 | 12 | Objective error counts |
| BGU-SKILLS | Knot tying; ring tower transfer; suturing | 938 | 18 | Identity/longitudinal analysis only |
| BGU-PatCut | Pattern cutting | 1,254 | 54 | Image-derived total cutting error |

The sum is 2,501 trials and 92 dataset-participants. Cohorts were distinct; the count does not assert that identity was linked across datasets.

# S3. Target provenance and construct language

| Dataset | Retained target | Measurement source | Permitted interpretation |
|---|---|---|---|
| JIGSAWS | GRS | Sum of six expert modified-OSATS ratings | Expert-rated trial performance |
| JIGSAWS | experience class | Self-declared label fixed by person | Person-level mechanism diagnostic |
| ROSMA | task errors | Observed task-specific error/drop count | Objective task performance |
| BGU-PatCut | total cutting error | Post-trial image deviation | Objective pattern-cutting accuracy |
| BGU-SKILLS | none | Source metrics derive from kinematics | No independent performance target |

The manuscript does not call ROSMA, BGU-PatCut, or BGU-SKILLS dataset-native metrics expert skill ratings. It makes no claim about clinical outcomes, competence, certification, or patient safety.

# S4. Deterministic preprocessing

Each loader emitted one record per complete trial with a source hash, participant and trial keys, task, repetition/session/condition metadata, outcome provenance, task duration, and two timestamped position streams. Source identifiers were used to build groups but were never model predictors. Committed fold files use 16-character SHA-256-derived opaque keys.

Task windows followed source annotations. For each arm, features were sampling rate; path length; speed mean, standard deviation, and 10th/50th/90th quantiles; mean and 90th-quantile absolute acceleration; mean and 90th-quantile absolute jerk; idle fraction below 0.001 m/s; workspace bounding-box volume; and recording-gap fraction. Gripper mean, standard deviation, range, and total variation were included where available. Cross-arm features were aligned-speed correlation and path-length asymmetry. Duration and arm sample counts were included as direct duration equivalents.

Non-finite rows and duplicate/backward timestamps were removed where applicable. A displacement spanning more than three median sampling intervals was excluded from path and derivative calculations. Interpolated values farther than 2.5 nominal samples from an observation were excluded from bimanual correlation. Imputation, scaling, residualization, identity fitting, and hyperparameter selection were trained within the applicable outer-training fold.

Two end-to-end extractions produced an identical private feature-matrix hash: `0c351007805f52f41459f622faa3c979f0b410685006763fbfcba1fc431a1e50`.

# S5. Fold construction and leakage protection

The same-participant manifest assigned complete trials by source repetition: five folds for JIGSAWS, six for ROSMA and BGU-SKILLS, and 24 for BGU-PatCut. Every participant-task group occupied at least two folds. The held-out-participant manifest used one fold per participant for JIGSAWS, ROSMA, and BGU-SKILLS and 10 balanced participant groups for BGU-PatCut. A participant was indivisible across tasks and trials in held-out evaluation.

Nested validation matched the intended outer unit. In a held-out-participant outer fold, inner splits also held out complete training participants. The outer test fold could not influence imputation, scaling, ridge penalty, logistic regularization, identity direction, projection rank, adversarial lambda, or probe hyperparameters. A leakage canary confirmed that identifier-derived columns were rejected from production predictors and yielded perfect identity prediction only when intentionally exposed.

# S6. Baseline models and diagnostics

Continuous targets used a training-fold mean/median reference, duration-only ridge, and full-feature ridge. Ridge alpha was selected from `{0.1, 1, 10, 100, 1000}`. JIGSAWS skill class used majority, duration-only multinomial logistic, and full-feature multinomial logistic models; C was selected from `{0.01, 0.1, 1, 10}`.

Fresh identity probes used multinomial logistic regression and random forest. Phase 3 forests used 200 trees; Phase 4 used 30 trees to limit the intervention grid’s compute cost, a dated deviation that retained the same nonlinear model family. Phase 3 ran 50 record-wise identity permutations per dataset-task, 50 continuous-outcome negative-control permutations per eligible dataset-task, and 200 paired participant-wise and record-wise skill permutations per JIGSAWS task.

The JIGSAWS replication compared six skill-accuracy and six GRS-MAE endpoints with the earlier study [@Hamilton2026Paper1]. Eleven of 12 were within frozen tolerances. Held-out-person needle-passing GRS MAE was 3.063 here versus 4.910 previously, a 1.8467-point difference beyond the 1.0-point tolerance. The present pipeline used 41 harmonized variables, transcription windows, exact repetition folds, fold-local preprocessing, and nested penalty selection; the earlier pipeline used 16 features at 5 Hz. This discrepancy is reported rather than treated as an independent replication success.

# S7. Intervention algorithms

## S7.1 I1: direct duration removal

I1 removed `duration_s`, `psm1_samples`, and `psm2_samples`. All remaining processing matched I0.

## S7.2 I2: fold-local duration residualization

Within each training fold, every non-duration feature was regressed on duration. The fixed coefficients were applied to validation and test rows. Scaling and prediction remained training fold local.

## S7.3 I3: linear identity-subspace removal

Within each outer-training fold, a regularized multinomial participant classifier produced a coefficient row space. Candidate ranks were `{0,1,2,4,8,16}`, clipped to the training fold’s maximum identity rank. For data with a performance target, inner validation retained ranks with task MAE within 0.05 training-target SD of rank zero and selected the one with lowest fresh linear identity accuracy, breaking ties toward smaller rank. For BGU-SKILLS, selection used identity accuracy alone. The fixed projection was applied to the outer test fold. This procedure resembles linear guarding by iterative nullspace projection [@Ravfogel2020], while using the prespecified coefficient-span implementation.

A random orthogonal projection removed the same fold-specific dimension. It controlled for capacity loss without targeting identity.

## S7.4 I4: adversarial summary representation

I4 used a 32-unit hidden layer, 8-unit latent layer, linear task head, and multinomial identity head. Gradient reversal multiplied the encoder’s identity-loss gradient by negative lambda while the identity head minimized cross-entropy [@Ganin2016]. Candidate lambda values were `{0,0.01,0.1,0.3,1.0}`. Two participant-safe inner splits and 30 selection epochs chose the lowest identity-head training accuracy among candidates with task MAE within 0.05 training-target SD of lambda zero; final models trained for 80 epochs at learning rate 0.01 and weight decay 0.0001. Three fixed seeds were used. Controls were the same architecture at lambda zero and the selected lambda with shuffled identity labels.

# S8. Verification and locked primary decision

Representations were frozen before fresh probes were trained. I4 versus its capacity control changed linear balanced accuracy by −0.048 (95% interval −0.082 to −0.015) and nonlinear accuracy by −0.003 (−0.038 to +0.032). Because the nonlinear interval did not verify reduction, I4 failed the two-probe rule. I3 versus I0 changed linear accuracy by −0.184 (−0.215 to −0.151) and nonlinear accuracy by −0.138 (−0.175 to −0.098), so I3 became the primary comparison before held-out task effects were inspected.

The dimension-matched random projection was worse than I3 by +0.167 on the linear probe and +0.149 on the nonlinear probe. Duration removal and residualization did not reproduce I3’s joint reduction.

# S9. Inference

The independent resampling unit was the participant. Participant-average metrics gave each participant equal weight irrespective of trial count. Intervals used 2,000 percentile bootstrap replicates within dataset-task. For identity verification, groups were averaged equally and I4 additionally averaged its three seeds. Leave-one-participant summaries were calculated for every primary estimand.

The held-out-task standardized effect for trial *i* was

`(|y_i - prediction_I3_i| - |y_i - prediction_I0_i|) / SD(y_training_for_outer_fold)`.

Negative values favor I3. Participant means were then averaged. Native-scale effects used the same paired numerator without standardization. Protocol gaps used the analogous held-out minus same-participant error after protocol-specific training-fold standardization.

Empirical permutation *p* values used `(1 + count(null >= observed)) / (1 + number of permutations)` with the appropriate directional statistic. No correction across tasks was used because the analysis reports task-specific estimands and treats the permutation results as replicated diagnostics.

# S10. Full locked numerical results

## S10.1 Unsuppressed identity recovery

| Dataset/task | Linear BA | Nonlinear BA | Record-wise null median |
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

Each full-feature probe exceeded its 50-permutation record-wise null at empirical *p*=0.0196.

## S10.2 JIGSAWS skill permutations

| Task | Observed | Participant-wise median [95% range] | Record-wise median [95% range] | Empirical *p* |
|---|---:|---:|---:|---:|
| Knot Tying | 0.917 | 0.778 [0.610, 0.917] | 0.306 [0.167, 0.501] | 0.004975 |
| Needle Passing | 0.964 | 0.875 [0.750, 1.000] | 0.321 [0.143, 0.501] | 0.004975 |
| Suturing | 0.872 | 0.923 [0.846, 0.974] | 0.359 [0.179, 0.538] | 0.004975 |

## S10.3 Primary held-out-participant effects

| Dataset/task | Standardized I3−I0 MAE [95% interval] | Native I3−I0 MAE [95% interval] |
|---|---:|---:|
| BGU-PatCut / Pattern Cutting | +0.029 [−0.038, +0.091] | +487.183 [−648.849, +1,613.362] |
| JIGSAWS / Knot Tying | +0.042 [−0.039, +0.132] | +0.205 [−0.195, +0.604] |
| JIGSAWS / Needle Passing | +0.125 [−0.018, +0.290] | +0.618 [−0.045, +1.400] |
| JIGSAWS / Suturing | −0.083 [−0.352, +0.170] | −0.401 [−1.757, +0.938] |
| ROSMA / Pea on a Peg | +24.141 [−0.019, +72.407] | +28.858 [−0.020, +86.539] |
| ROSMA / Post and Sleeve | +0.009 [−0.125, +0.154] | +0.005 [−0.072, +0.086] |
| ROSMA / Wire Chaser I | +0.004 [+0.000, +0.011] | +0.003 [0.000, +0.008] |

The compatible ranges are the study’s practical precision statement. With no validated cross-dataset clinical threshold and no equivalence margin, intervals crossing zero are not evidence of equivalence. The pea-on-a-peg standardized result is dominated by small fold-specific training SDs and should be read with its native result and source anomaly.

## S10.4 Same-participant JIGSAWS skill effects

I3 minus I0 participant-average accuracy was −0.025 [−0.075, 0.000] for knot tying, 0.000 [0.000, 0.000] for needle passing, and +0.025 [−0.100, +0.125] for suturing. The direction was not consistent.

# S11. Robustness and influence analyses

Fold-local I3 selected positive rank in 112/144 outer folds. I4 selected nonzero lambda in 116/126 folds: 0.01 twice, 0.1 fourteen times, 0.3 forty-six times, and 1.0 fifty-four times; ten folds retained zero. Across I4 seeds, JIGSAWS skill-accuracy ranges were at most 0.179. Identity-probe seed ranges had median 0.072 and maximum 0.225.

Participant-level task effects, protocol gaps, identity effects, skill effects, and leave-one-participant summaries are in `results/locked/`. The 748,000 bootstrap replicate rows and 5,226 leave-one rows are preserved in machine-readable files. The supplement tables in `results/tables/` document fold composition, selected hyperparameters, missingness, and seed stability.

# S12. Deviations from the prospective plan

1. Phase 0 and Phase 1 were completed in one working session. The protocol was still frozen before model fitting.
2. Source inspection required explicit non-finite-row and time-gap handling. These rules were fixed before modeling and tested deterministically.
3. The initial same-participant fold draft rotated assignments by participant. It was corrected to exact repetition mapping before the first Phase 3 prediction.
4. I4 used a summary-feature MLP instead of the planned sequence encoder because Phase 2 had frozen summary representations rather than resampled sequences. This limits claims to summary features.
5. Phase 4 nonlinear probes used 30 trees rather than Phase 3’s 200 to control intervention-grid cost. The nonlinear model family and participant-safe tuning remained unchanged.
6. Phase 5 regenerated inference from hashed Phase 3/4 predictions rather than refitting under a new commit. This preserved the recorded generating commit and enabled exact reproducibility.
7. Optional BGU component-outcome post hoc models and per-epoch I4 loss exports were not produced. Neither was required for the locked primary endpoint.

No deviation changed the participants, primary targets, validation unit, primary estimand, participant-level inference, or prespecified I4-to-I3 fallback rule after task effects were inspected.

# S13. Relationship to the earlier JIGSAWS study

The earlier manuscript, “What does a surgical skill model measure? Quantifying identity confounding and miscalibration on JIGSAWS,” analyzed the same 103 JIGSAWS trials [@Hamilton2026Paper1]. It reported same-person versus held-person performance, identity recovery, label permutations, calibration, selective prediction, and a commercial zero-shot model. The present work reproduces its central protocol/identity diagnosis using a different 41-feature representation and exact fold-local pipeline, then extends the question to three external datasets and directly intervenes on identity representations. It does not reuse or re-report the commercial model, calibration, or selective-prediction analyses. The JIGSAWS results are therefore overlapping replication and extension evidence, not an independent cohort.

# S14. Reproduction

After authorized data acquisition and environment setup, run:

```bash
.venv/bin/python scripts/run_phase5_locked.py
.venv/bin/python scripts/validate_phase6.py
```

The Phase 5 command validates Phases 1–4, verifies private artifact hashes, builds Phase 5 twice, compares every output hash, runs the test suite, and applies the Phase 5 validator. The Phase 6 validator checks manuscript structure, bibliography keys, locked numerical statements, overlap disclosure, construct language, and the claim-evidence/reporting matrices.
