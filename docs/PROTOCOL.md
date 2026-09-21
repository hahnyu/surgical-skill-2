# Prospective protocol: operator identity suppression and generalization

**Frozen version:** 1.0  
**Freeze date:** 2026-09-21  
**Authoritative source:** `SECOND_PAPER_CODEX_MASTER_PLAN.md`, SHA-256
`61c40a77dc9d2ede9ab72191ff9ecf99862c256e86341fa86817d1a6ace0b2ab`

This document fixes the confirmatory design before predictive outcomes are
generated in this repository. Dataset eligibility and target provenance are
resolved at the Phase 1 gate, but cannot alter the hypotheses, endpoint
hierarchy, validation unit, intervention family, or exclusion principles below
without a dated entry in `docs/DEVIATIONS.md`.

## Research question and claims

When repeated surgical performances from the same operators are available, how
much apparent predictive performance is attributable to operator-specific
information, and does suppressing that information improve prediction for an
unseen operator?

The study distinguishes expert-rated surgical skill from objective task
performance. It will not claim clinical validity, patient-outcome validity,
absence of identity information after a failed probe, or generalization beyond
the included datasets and modalities.

## Units, eligible data, and outcomes

The observational unit is a complete task trial. The participant is the
independent sampling unit for uncertainty. Frames, windows, gestures, and time
points from a trial remain in one fold. Analyses are task specific; pooled
secondary analyses require dataset and task indicators.

JIGSAWS is the anchor dataset. Its primary outcome is trial-level total GRS
(modified OSATS), analyzed continuously. The self-declared novice/intermediate/
expert label is a secondary mechanistic diagnostic because it is constant
within participant.

An external target is eligible only when participant identifiers and trial-level
outcomes are available and provenance is unambiguous. Preference order is:
blinded expert rating; independent error or accuracy measurement; validated
composite with a documented formula; then a dataset-native objective measure
with narrow construct claims. Completion time cannot be both input and outcome.
Targets calculated from planned kinematic predictors are ineligible for the
primary external performance analysis unless an independent component can be
isolated. Repetition, session, perturbation condition, and duration will not be
relabeled as skill.

## Inputs and preprocessing

Primary inputs are kinematics. Two fixed feature families will be used:

1. Harmonized summaries: duration, path length, speed, acceleration, jerk,
   idle fraction, workspace spread, bimanual coordination, asymmetry, gripper
   activity, and economy-of-motion measures where available.
2. One compact sequence encoder (1D CNN, GRU, or TCN selected for engineering
   feasibility before final outcomes), with global pooling and linear heads.

Every transform—including scaling, imputation, filtering, residualization,
feature selection, identity direction fitting, and hyperparameter selection—is
fit using the applicable training fold only.

## Validation protocols

Every eligible dataset/task receives paired evaluation:

1. **Same-participant:** a source-defined repetition split where valid, or
   trial-grouped folds deliberately retaining every participant on both sides.
2. **Held-out-participant:** leave one participant out, or participant-grouped
   K-fold if leave-one-out is computationally prohibitive.
3. **Held-out-session:** optional only where sessions can be separated without
   participant leakage.

Nested validation follows the intended generalization unit. All reported
predictions are out of fold. The outer test participant never contributes to
preprocessing, projection, tuning, or stopping.

## Fixed model families

- Training-fold mean/median reference.
- Duration-only linear or ordinal reference where duration is not part of the
  target formula.
- Ridge or elastic-net regression for continuous outcomes.
- Multinomial logistic regression for categorical outcomes.
- One compact sequence model as defined above.

No architecture tournament is permitted. Gradient boosting may be added only
through a dated deviation recorded before predictive outcomes are inspected.

## Fixed interventions

- **I0, unsuppressed:** ordinary training with the predeclared feature set.
- **I1, direct duration removal:** remove duration and exact algebraic
  equivalents.
- **I2, duration residualization:** within each training fold, regress every
  non-duration feature on duration and apply the fixed transform to validation
  and test data.
- **I3, linear identity-subspace removal:** fit a regularized multinomial
  training-participant classifier, construct the span of its coefficients,
  choose the number of directions in the inner loop, and project those
  directions out before applying the frozen transform to the outer test fold.
- **I4, adversarial identity suppression:** compact sequence encoder with a
  gradient-reversal identity head; inner-loop lambda grid
  `{0, 0.01, 0.1, 0.3, 1.0}`.

I3 is the primary mechanistic intervention. I4 is the planned strongest method
only if it trains successfully and reduces at least one fresh identity probe.
If I4 fails that verification, I3 becomes the primary I0 comparison before task
performance is inspected. An optional disentangled I5 remains exploratory.

After each intervention, freeze the representation and train fresh linear and
nonlinear identity probes. The required nonlinear probe is a random forest or a
shallow MLP selected before final analysis. Report balanced accuracy, macro
accuracy/F1, log loss, and empirical permutation references.

## Hypotheses and estimands

- **H1 Protocol gap:** same-participant evaluation is more favorable than
  held-out-participant evaluation. Estimand: participant-averaged paired metric
  difference for the same model and features.
- **H2 Identity recoverability:** unsuppressed kinematics identify operators
  above an empirical chance reference. Estimand: probe metric minus the median
  participant-label permutation null.
- **H3 Identity-confounding null:** for person-level labels, participant-wise
  permutation preserves more same-participant performance than record-wise
  permutation. Continuous longitudinal targets require a separately justified
  exchangeable grouped permutation.
- **H4 Intervention efficacy:** suppression reduces fresh-probe identity
  recovery versus I0.
- **H5 New-user utility:** suppression may help, harm, or leave unchanged
  held-out-participant prediction. Estimand: MAE(suppressed) minus MAE(I0), where
  negative favors suppression.
- **H6 Apparent same-user utility:** suppression is expected to reduce
  same-participant JIGSAWS person-level skill accuracy when identity-compatible
  information supported lookup.

## Primary endpoint hierarchy

1. Change in held-out-participant MAE under the strongest successfully verified
   suppression intervention versus I0, estimated within dataset/task and
   synthesized across eligible targets.
2. Change in nonlinear identity-probe balanced accuracy.
3. Change in same-participant person-level skill accuracy on JIGSAWS.

All remaining endpoints are secondary or exploratory. Report full estimates
and participant-level uncertainty even for null or harmful effects.

## Exclusions and missingness

Exclude a trial only when it is missing the required input, participant ID, or
primary target; cannot be matched unambiguously; is corrupt/unreadable; or is
explicitly invalidated by source documentation. Never remove an outlier solely
because its outcome is extreme. Source-defined analysis exclusions are reported
separately from deposited-file availability. Any discretionary exclusion or
correction requires a dated deviation before final outcomes are inspected.

## Controls and inference

The confirmatory controls are participant-wise and record-wise label
permutations, a random orthogonal projection that removes the same dimension as
I3, and a capacity-matched sequence model without gradient reversal for I4.
Uncertainty resamples participants, not frames or trials. Primary synthesis uses
task-level paired suppression effects while preserving dataset/task identity;
the exact meta-analytic estimator will be fixed before Phase 3 modeling.

## Governance and stopping rules

Raw datasets are never committed or uploaded to model APIs. Release only
artifacts allowed by source agreements. Phase 1 chooses:

- **Plan A:** JIGSAWS plus at least one external dataset has a defensible,
  non-tautological trial-level performance target and participant IDs.
- **Plan B:** only JIGSAWS supplies a defensible skill target; other datasets
  support identity and robustness audits.
- **No-go:** external data cannot support a meaningful complementary analysis.

No model training begins before the Phase 1 report is reviewed.

