---
title: "Operator identity and out-of-user generalization in automated surgical skill assessment: a multi-dataset evaluation"
bibliography: references.bib
date: 2026-09-26
---

> **Submission metadata:** author names, affiliations, corresponding-author details, funding, conflicts of interest, and the applicable institutional ethics determination must be completed before submission. The scientific text and numerical results below are locked to Phase 5.

# Abstract

**Purpose:** Repeated recordings from the same operator can let surgical-performance models use operator-specific motion patterns. We tested whether operator identity was recoverable from surgical kinematics and whether suppressing that information improved prediction for unseen operators.

**Methods:** We retrospectively analyzed 2,501 complete dry-lab trials representing 92 dataset-participants from four distinct cohorts: JIGSAWS (103 trials; expert-rated Global Rating Scale [GRS]), ROSMA (206 trials; observed task errors), BGU-PatCut (1,254 trials; image-derived cutting error), and BGU-SKILLS (938 trials; identity analysis only). We compared same-participant with held-out-participant evaluation, measured identity with nested fresh linear and random-forest probes, and used participant-wise versus record-wise permutations for JIGSAWS person-level skill labels. Prespecified interventions removed duration, residualized features on duration, projected out a learned linear identity subspace (I3), or used adversarial representation learning (I4). The primary utility estimand was participant-average held-out-participant mean absolute error (MAE) for verified suppression versus the unsuppressed model. Intervals used 2,000 participant bootstrap replicates.

**Results:** Unsuppressed identity balanced accuracy exceeded its record-wise permutation null in all ten dataset-task groups (linear range 0.228–0.944; nonlinear range 0.381–0.844; each empirical *p*=0.0196). In JIGSAWS, participant-wise label permutations retained substantially higher same-participant skill accuracy than record-wise permutations (median paired differences 0.444–0.538; each empirical *p*=0.004975). I3 reduced fresh linear identity accuracy by 0.184 (95% interval 0.151–0.215) and nonlinear accuracy by 0.138 (0.098–0.175). I4 did not pass the prespecified two-probe verification rule. For I3 versus the unsuppressed model, held-out-participant standardized MAE point estimates favored I3 in one of seven eligible tasks and favored the unsuppressed model in six. Six intervals crossed zero; the wire-chasing estimate was +0.004 (0.000–0.011), where positive values favor the unsuppressed model.

**Conclusion:** Operator identity was strongly recoverable from summary kinematics, and targeted projection reduced fresh-probe recovery. That verified reduction did not consistently improve unseen-operator prediction. Identity diagnostics and suppression tests answer different questions; neither same-user performance nor reduced probe accuracy alone establishes improved generalization.

**Keywords:** surgical skill assessment; operator identity; out-of-user validation; domain generalization; kinematics; representation learning

# Introduction

Automated assessment could make technical feedback more frequent and reproducible, but evidence from simulated tasks does not yet establish clinical validity. Reviews describe heterogeneous targets, small cohorts, and inconsistent validation, with many studies classifying experience groups rather than predicting independently rated performance [@Lam2022]. Shared resources such as JIGSAWS have enabled comparison across methods [@Ahmidi2017], while newer datasets expand the range of tasks, operators, and measurement systems [@RivasBlanco2023; @Sharon2025].

A recurring design issue is repeated observations from each operator. Motion signatures can be stable within a person. If records from one operator appear in both training and test folds, a model can exploit identity-compatible structure, particularly when the target itself is constant within person. Such behavior is one instance of shortcut learning: a decision rule performs well under a benchmark split while relying on information that may not transfer to the intended setting [@Geirhos2020]. A deployment claim about a new operator therefore requires an evaluation split that withholds that operator from all preprocessing, tuning, and fitting.

Two diagnostics help identify this risk but do not establish that an outcome model relies on identity. First, a same-participant versus held-out-participant performance gap indicates protocol sensitivity. Second, an identity probe asks whether the representation contains operator-identifying information. A strong probe can coexist with an outcome model that ignores identity; a weak probe can miss nonlinear or otherwise inaccessible identity information. Formal label permutations can sharpen the interpretation when the outcome is person-constant: participant-wise permutation preserves identity-to-label lookup while breaking the original skill assignment, whereas record-wise permutation breaks both.

An earlier JIGSAWS-only study from this project reported protocol gaps, high identity recoverability, label-permutation behavior, calibration, and selective-prediction findings [@Hamilton2026Paper1]. That work diagnosed a risk but did not test whether removing identity-compatible information improved held-out-user prediction. It also used the same 103 JIGSAWS trials analyzed here, so the JIGSAWS component of the present study is a replication and mechanistic extension, not independent external validation. The present analysis adds ROSMA, BGU-SKILLS, and BGU-PatCut; replaces the earlier 16-feature pipeline with a harmonized 41-variable representation; and prespecifies identity-suppression interventions, fresh probes, negative controls, and participant-level inference. Calibration, selective prediction, and commercial zero-shot predictions from the earlier study are outside the present scope.

We asked whether operator identity is recoverable across multiple surgical-training datasets and whether suppressing that information improves prediction for an unseen operator. The prespecified hypotheses were that same-participant evaluation would be more favorable than held-out-participant evaluation; identity would be recoverable above an empirical null; participant-wise permutations would preserve JIGSAWS person-level skill classification more than record-wise permutations; verified suppression would reduce fresh-probe identity recovery; and suppression could help, harm, or leave unchanged held-out-operator utility. We further tested whether suppression reduced apparent same-participant JIGSAWS skill accuracy.

# Related work

Surgical data science aims to turn multimodal procedural data into reproducible measurements and decision support [@MaierHein2017]. Yet “skill” is not a single interchangeable target. JIGSAWS provides expert modified-OSATS ratings and self-declared experience classes [@Ahmidi2017]. ROSMA records task-specific error counts [@RivasBlanco2023; @ROSMAData2022]. BGU-PatCut measures deviation from a cutting template using a post-trial gauze image [@SharonPatCut2024; @PatCutData2024]. BGU-SKILLS tracks longitudinal training metrics, several of which are transformations of the same kinematics used as predictors [@Sharon2025; @BGUSkillsData2025]. We therefore reserve “expert-rated skill” for JIGSAWS GRS and describe the external outcomes as objective task-performance measures.

Validation protocols encode the intended user. Trial-level or repetition-level folds estimate performance on further records from represented operators; participant-grouped folds estimate performance on an unseen operator. Participant identity can also be evaluated directly. Because participants differ in trial count, balanced accuracy and participant-level resampling are preferable to record-weighted summaries.

Identity removal is related to representation guarding and domain invariance. Iterative nullspace projection removes directions used by repeated linear classifiers [@Ravfogel2020]. Domain-adversarial training uses gradient reversal so an encoder supports the main task while frustrating a domain or identity classifier [@Ganin2016]. Neither method guarantees absence of identity under every decoder. Fresh linear and nonlinear probes are therefore necessary after the representation is frozen, and matched random projection helps distinguish targeted removal from generic dimensionality reduction.

# Methods

## Study design and protocol

This retrospective multi-dataset benchmark followed a protocol frozen before predictive modeling (`protocol-v1`, 21 September 2026). The complete trial was the observational unit and the participant was the independent unit for uncertainty. Frames and time points from one trial remained in one fold. Analyses were task specific. The protocol, dated deviations, configuration files, and locked artifact hashes are available in the repository.

## Datasets, participants, and outcomes

The analysis included 2,501 trials representing 92 dataset-participants across four distinct cohorts (Table 1). JIGSAWS contributed knot tying (36 trials, 8 operators), needle passing (28 trials, 7 operators), and suturing (39 trials, 8 operators). Its continuous outcome was total expert-rated GRS, the sum of six modified-OSATS elements; self-declared novice/intermediate/expert status was used only for the person-level mechanistic analysis.

ROSMA contributed pea on a peg (71 trials), post and sleeve (65), and wire chaser I (70) from 12 participants. The eligible outcome was the observed task-specific error count. Completion time and source composite scores were excluded because duration was directly available to the predictors. BGU-PatCut contributed 1,254 pattern-cutting trials from 54 participants; total cutting error was measured from a separate post-trial gauze scan. BGU-SKILLS contributed 938 source-included trials from 18 residents across knot tying, ring tower transfer, and suturing. It had no eligible independent performance target because its reported timing and motion metrics were derived from the planned inputs, so it contributed only to identity and longitudinal robustness analyses.

Trials were included when kinematics, participant ID, task identity, and—where required—the eligible outcome could be matched unambiguously. Source-documented invalid or excluded trials were omitted. No record was excluded because its outcome or model residual was extreme. One ROSMA pea-on-a-peg trial contained finite coordinate spikes in the deposited data; it remained in the locked analysis.

## Kinematic preprocessing and features

Task windows followed source annotations. JIGSAWS used transcription boundaries at 30 Hz; ROSMA parsed timestamps and removed non-finite or duplicate/backward-time rows; BGU-SKILLS used source task start and finish events; BGU-PatCut used segmentation boundaries and aligned jaw samples to positions. Steps spanning more than three median sampling intervals were excluded from path and derivative calculations so missing intervals were not interpreted as motion.

The harmonized representation contained 41 available variables: duration and sample counts; per-arm sampling rate, path length, speed summaries, acceleration, jerk, idle fraction, workspace volume, gap fraction, and gripper summaries where present; plus bimanual speed correlation and path-length asymmetry. Missing values were imputed and variables standardized within each training fold. Participant identifiers, filenames, conditions, sessions, repetitions, and targets were excluded from model inputs.

## Validation and baseline models

Same-participant folds preserved complete trials while retaining each participant on both sides: five repetition folds for JIGSAWS, six for ROSMA and BGU-SKILLS, and 24 for BGU-PatCut. Held-out-participant evaluation used leave-one-participant-out folds for JIGSAWS, ROSMA, and BGU-SKILLS, and 10 participant-grouped folds for BGU-PatCut. Inner validation followed the outer generalization unit.

Continuous outcomes used a training-fold mean reference, duration-only ridge regression, and ridge regression on all harmonized features; the ridge penalty was selected inside each outer fold from 0.1, 1, 10, 100, and 1,000. JIGSAWS person-level skill used majority, duration-only multinomial logistic, and full-feature multinomial logistic models with nested regularization selection. All reported predictions were out of fold.

## Protocol-gap, identity, and permutation diagnostics

Protocol gaps compared participant-average error for the same ridge model under paired same-participant and held-out-participant evaluation, standardized using the applicable outer-training target standard deviation. Identity probes predicted the participant from unsuppressed features. The linear probe was multinomial logistic regression; the nonlinear probe was a 200-tree random forest. Hyperparameters were selected within the outer training data. Balanced accuracy was the primary identity metric; because each class was one participant and results were averaged by participant, it equals participant-average accuracy.

For each dataset-task group, 50 record-wise identity-label permutations supplied an empirical null. For JIGSAWS person-level skill, 200 paired participant-wise and record-wise permutations were evaluated under the same-participant protocol. Participant-wise permutation assigned one shuffled label to all records of a participant; record-wise permutation shuffled labels among trials. We did not apply participant-wise permutations to outcomes that varied within participant because the required grouped exchangeability was not established.

## Identity interventions and verification

I0 was the unsuppressed representation. I1 removed duration and exact sample-count equivalents. I2 regressed each remaining feature on duration using training data and retained the residuals. I3 fit a regularized multinomial participant classifier in each training fold, constructed its coefficient span, and projected out *k* identity directions. Inner validation chose the smallest *k* attaining the lowest fresh linear identity accuracy among candidates whose task MAE was within 0.05 training-target standard deviations of I0; candidates were 0, 1, 2, 4, 8, and 16, clipped to the available identity rank. A random orthogonal projection removed the same dimension as a negative control.

I4 used a compact multilayer perceptron over the frozen summary features, with a 32-unit hidden layer, an 8-unit latent representation, a task head, and a gradient-reversal participant-identity head. This summary-feature MLP replaced the planned sequence encoder because Phase 2 froze summary rather than resampled sequence representations; the deviation was recorded before Phase 4 results. Lambda was selected from 0, 0.01, 0.1, 0.3, and 1.0 under the same 0.05-standard-deviation utility constraint. A lambda-zero network controlled for capacity, and a shuffled identity head controlled for the extra training pathway. Three seeds were used.

After fitting, each representation was frozen and evaluated with newly trained multinomial-logistic and 30-tree random-forest probes. The prespecified primary comparison required the candidate to reduce both fresh probes. I4 was considered first; if it failed, I3 versus I0 became primary before task effects were inspected.

## Estimands and statistical analysis

The primary utility estimand was participant-average paired absolute-error difference, MAE(I3) minus MAE(I0), under held-out-participant evaluation. Negative values favor suppression. For comparison across tasks, each trial-level difference was divided by the outcome standard deviation estimated without that outer test fold. Native-unit effects were retained. Results were not pooled because GRS points, error counts, and image-derived cutting error represent different constructs and because the standardized ROSMA pea-on-a-peg denominator was unstable.

Intervals were percentile intervals from 2,000 participant bootstrap replicates within each dataset-task group. Leave-one-participant estimates assessed influence. Empirical permutation *p* values used the plus-one correction. The analysis was estimation focused; no equivalence margin or minimum clinically important difference exists for these heterogeneous simulation outcomes. Null intervals are therefore interpreted as compatible ranges rather than proof of no effect.

## Reproducibility and reporting

The locked runner verifies SHA-256 hashes of all out-of-fold prediction inputs, regenerates figures and tables twice, compares byte hashes, runs the test suite, and validates required outputs. Trial-level predictions remain local where source terms or participant privacy limit redistribution. Reporting follows an adapted TRIPOD+AI checklist [@Collins2024].

# Results

## Feasibility and target audit

All four datasets contained repeated complete trials and stable participant keys. JIGSAWS supplied the only expert-rated outcome. ROSMA errors and BGU-PatCut total cutting error were retained as narrower objective task-performance outcomes. BGU-SKILLS was retained for identity analysis without relabeling its kinematic metrics as independent skill targets. The final cohort contained 2,501 trials: 103 JIGSAWS, 206 ROSMA, 938 BGU-SKILLS, and 1,254 BGU-PatCut.

## Protocol gap

For continuous outcomes, the standardized held-out-participant minus same-participant ridge MAE was positive in six of seven eligible tasks (Figure 2). Native-unit JIGSAWS gaps were +0.770 GRS points for knot tying, +0.174 for needle passing, and +1.722 for suturing; the participant interval excluded zero only for suturing (+0.204 to +3.413). JIGSAWS person-level skill classification showed larger gaps: same-participant versus held-out-participant accuracy was 0.917 versus 0.444 for knot tying, 1.000 versus 0.464 for needle passing, and 0.872 versus 0.462 for suturing. Participant-average gaps were +0.419 (0.063–0.775), +0.479 (0.214–0.757), and +0.400 (0.150–0.675), respectively.

## Identity recovery and formal nulls

Identity was recoverable in every dataset-task group (Figure 3; Table 4). Unsuppressed linear balanced accuracy ranged from 0.228 for ROSMA wire chaser to 0.944 for JIGSAWS suturing, and nonlinear accuracy ranged from 0.381 for ROSMA post and sleeve to 0.844 for JIGSAWS suturing. Every full-feature probe exceeded its 50-permutation record-wise null at the attainable empirical floor (*p*=0.0196). Duration-only identity accuracy ranged from 0.056 to 0.225 and did not explain the full-feature signal.

The JIGSAWS skill permutation test separated person-compatible lookup from trial-level signal. For knot tying, observed same-participant accuracy was 0.917; the participant-wise null median was 0.778 (95% permutation range 0.610–0.917) and the record-wise median was 0.306 (0.167–0.501). Corresponding values were 0.964, 0.875 (0.750–1.000), and 0.321 (0.143–0.501) for needle passing, and 0.872, 0.923 (0.846–0.974), and 0.359 (0.179–0.538) for suturing. Median paired participant-wise minus record-wise differences were +0.444, +0.536, and +0.538; each empirical *p*=0.004975.

## Intervention verification

I4 adversarial training reduced fresh linear identity accuracy by 0.048 (95% participant interval 0.015–0.082) relative to its lambda-zero capacity control, but its nonlinear change was −0.003 (−0.038 to +0.032). It therefore failed the two-probe verification rule. I3 became the locked primary intervention. Relative to I0, I3 reduced fresh linear balanced accuracy by 0.184 (0.151–0.215) and nonlinear balanced accuracy by 0.138 (0.098–0.175), averaging dataset-task groups equally (Figure 4).

Direct duration removal did not reduce identity consistently: mean linear and nonlinear changes versus I0 were +0.018 and +0.002. Duration residualization changed them by +0.013 and −0.025. The dimension-matched random projection changed identity by −0.018 and +0.011, leaving linear and nonlinear recovery 0.167 and 0.149 higher than I3. These controls attribute the verified I3 probe change to targeted learned directions rather than removal of duration or dimension alone.

## Held-out-participant utility

I3 did not consistently improve held-out-participant prediction (Figure 5; Table 5). Standardized MAE differences were +0.029 (−0.038 to +0.091) for BGU-PatCut pattern cutting; +0.042 (−0.039 to +0.132), +0.125 (−0.018 to +0.290), and −0.083 (−0.352 to +0.170) for JIGSAWS knot tying, needle passing, and suturing; and +24.141 (−0.019 to +72.407), +0.009 (−0.125 to +0.154), and +0.004 (+0.000 to +0.011) for ROSMA pea on a peg, post and sleeve, and wire chaser. Thus one point estimate favored I3 and six favored I0. Six intervals crossed zero. The wire-chaser interval met zero at its displayed lower bound.

Native-scale paired MAE differences were +487.183 cutting-error units (−648.849 to +1,613.362), +0.205 GRS points (−0.195 to +0.604), +0.618 (−0.045 to +1.400), −0.401 (−1.757 to +0.938), +28.858 ROSMA errors (−0.020 to +86.539), +0.005 (−0.072 to +0.086), and +0.003 (0.000 to +0.008), in the same task order.

The ROSMA pea-on-a-peg standardized estimate is not comparable in magnitude with the others. The outcome was zero inflated and some outer-training target standard deviations were small; the retained finite coordinate spikes also destabilized ridge predictions. Its wide interval is compatible with negligible through very large harm on the standardized scale. Across the other tasks, the intervals likewise do not establish equivalence: for example, the compatible standardized ranges include −0.038 to +0.091 for PatCut and −0.352 to +0.170 for JIGSAWS suturing. With only seven or eight JIGSAWS participants per task, the analysis could not resolve modest effects precisely.

## Same-participant skill and robustness

For JIGSAWS person-level skill, I3 changed participant-average same-participant accuracy by −0.025 (−0.075 to 0.000) for knot tying, 0.000 (0.000 to 0.000) for needle passing, and +0.025 (−0.100 to +0.125) for suturing (Figure 6). The prespecified expectation of a consistent reduction was not supported.

I3 selected a positive number of identity directions in 112 of 144 outer folds. I4 selected nonzero lambda in 116 of 126 folds, but fresh nonlinear probes showed that confusing the training adversary did not establish invariance. Leave-one-participant estimates, seed ranges, fold composition, missingness, and hyperparameter selections are provided in the supplement.

# Discussion

Across four surgical-training datasets, operator identity was recoverable from harmonized kinematic summaries. In JIGSAWS, the contrast between participant-wise and record-wise permutations showed that person-compatible structure could sustain high same-participant classification after the original experience labels were destroyed. Targeted linear projection then reduced both fresh identity probes. The central intervention result was nevertheless negative: reduced identity recovery did not consistently improve prediction for unseen operators.

This distinction matters. Protocol gaps and identity probes diagnose opportunities for a shortcut; they do not show that a particular outcome model uses the recoverable identity information. Conversely, removing a learned identity subspace can discard stable motion components that legitimately predict performance. The held-out-participant point estimates, which favored the unsuppressed model in six of seven tasks, are consistent with that tradeoff. Because most intervals include both benefit and harm, the data do not justify a universal claim that identity suppression damages prediction either.

The adversarial result illustrates another limit. The I4 identity head was trained jointly with the encoder and its linear reduction appeared favorable, yet a separately fitted nonlinear probe showed essentially no reduction. An adversary can be fooled within its own hypothesis class while identity remains decodable by another model. Fresh probes, prespecified verification, and a capacity-matched control prevented the task result from being presented as evidence of successful adversarial invariance.

The same-participant JIGSAWS skill result also resisted a simple mechanism. I3 did not consistently reduce person-level accuracy even though participant-wise permutations showed strong structural confounding and I3 reduced identity probes. The representation may retain nonlinear identity, person-level labels may correlate with genuine stable performance patterns, or the outcome classifier may use features outside the removed linear span. These explanations cannot be separated with eight operators.

Heterogeneity across tasks was expected and is scientifically relevant. JIGSAWS GRS is an expert rating of trial performance. ROSMA errors are sparse observed counts. PatCut total error is an image-derived geometric deviation. The tasks differ in platform, population, sensor sampling, preprocessing, and repetition structure. Pooling their standardized effects would conceal these differences, particularly the unstable pea-on-a-peg denominator. The task-specific forest is therefore the primary synthesis.

For model development, held-out-participant evaluation should match claims about new users. Same-participant results remain useful when the intended system personalizes to a known trainee, but they answer a different question. Identity probes and participant-wise nulls can reveal whether a benchmark permits person lookup. If suppression is proposed, its success should be verified independently and its task utility measured rather than assumed.

## Limitations

The number of independent participants was small despite 2,501 trials: JIGSAWS had seven or eight participants per task, ROSMA 12, and BGU-SKILLS 18. Repeated trials improve within-person estimation but do not replace independent people. Most intervention intervals therefore allow effects that could matter in either direction, no equivalence margin was prespecified, and the study cannot establish absence of benefit or harm.

The outcomes are heterogeneous. Only JIGSAWS GRS was expert rated. ROSMA error counts and BGU-PatCut cutting error measure narrower aspects of task performance, and external dataset scores may imperfectly represent the constructs of interest. Person-level JIGSAWS experience categories are self-declared and constant within participant, so they are a mechanism diagnostic rather than trial-level skill ground truth.

All tasks were simulation or dry-lab exercises. The results do not establish prediction quality, fairness, educational benefit, or patient-outcome validity in clinical surgery. The datasets differ in robot or research platform, task, sensors, sampling, preprocessing, participant population, and data-collection context. This variation broadens the audit but prevents attribution of between-dataset differences to a single factor.

Identity can encode genuine stable skill, anatomy-independent motor strategy, prior training, or measurement artifacts. Removing identity-compatible information can therefore remove legitimate predictive signal. I3 guards against selected linear identity directions only; lower performance of fresh linear and random-forest probes does not prove that all identity information is absent. Similarly, adversarial training does not guarantee invariance beyond the fitted adversary or tested probes.

The analysis used harmonized summary features. The planned sequence intervention was replaced before Phase 4 with a summary-feature MLP because resampled sequence representations had not been frozen in Phase 2. Deep sequence or video representations might expose different identity and task structure. One ROSMA trial contained source coordinate spikes retained under the prospective no-post-result-exclusion rule, and the sparse pea-on-a-peg outcome yielded unstable standardized effects.

No prospective data collection, independent clinical cohort, or deployment study was performed. Demographic attributes were unavailable, so performance disparities and algorithmic fairness across demographic groups could not be assessed. The study evaluated participant identity as a methodological grouping variable, not as a protected attribute.

# Conclusion

Operator identity was recoverable across all examined kinematic task groups, and JIGSAWS same-participant skill classification retained substantial accuracy under participant-wise label permutation. Linear identity-subspace projection reduced identity recovery by fresh linear and nonlinear probes, but did not consistently improve prediction for unseen operators. Claims about generalization should therefore rest on participant-held-out evaluation, while claims about invariance require independent probes and task-utility tests.

# Declarations

**Ethics:** This was a secondary analysis of deidentified research datasets with no new participant contact or data collection. The repository does not contain a new institutional ethics determination. The authors must confirm and report the applicable institutional and journal requirements before submission.

**Patient and public involvement:** No patient or public contributors were involved in designing, conducting, reporting, or disseminating this retrospective benchmark analysis.

**Funding:** To be completed by the authors before submission; funding information was not present in the analysis record.

**Competing interests:** To be completed by the authors before submission.

**Author contributions:** To be completed using the journal’s requested taxonomy.

**Data and code availability:** See `data_code_availability.md`. Code, aggregate results, fold manifests, and artifact hashes are available at <https://github.com/hahnyu/surgical-skill-2>. Raw JIGSAWS data require the source agreement and are not redistributed. The public external datasets remain available from their cited repositories.

# Tables and figures

The submission-ready source tables are `../results/tables/phase5_table1_datasets.csv` through `phase5_table5_interventions.csv`. Figure sources are the six deterministic SVG files in `../results/figures/`:

1. Study design and analysis flow.
2. Same-participant versus held-out-participant protocol gap.
3. JIGSAWS participant-wise and record-wise permutation distributions.
4. Task utility versus fresh-probe identity reduction.
5. Task-specific held-out-participant intervention effects.
6. JIGSAWS mechanism summary.
