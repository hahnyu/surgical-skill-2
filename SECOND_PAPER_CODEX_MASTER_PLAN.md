# Second-paper master specification for Codex

## Working title

**Does suppressing operator identity improve generalization in automated surgical skill assessment? A multi-dataset shortcut audit and intervention study**

Alternative conservative title if mitigation does not improve held-out-user performance:

**Operator identity and out-of-user generalization in automated surgical skill assessment: a multi-dataset evaluation**

## Status and purpose of this document

This file is the complete research and implementation brief for a coding agent. It is intended to take the project from dataset verification through a reproducible analysis, figures, manuscript, and release checklist.

The project must use only existing public or access-controlled public research datasets. It must not recruit participants, collect new human data, contact participants, scrape restricted data, or bypass dataset access agreements. The researcher should be able to execute the work independently.

This is a **prospective protocol**. Do not silently change outcomes, datasets, exclusion rules, features, validation schemes, or statistical tests after seeing results. Necessary deviations must be entered in `docs/DEVIATIONS.md` with date, reason, whether outcomes had been inspected, and likely direction of bias.

---

# 1. Executive decision

## 1.1 Recommended publication boundary

Paper 1 is a focused diagnosis on JIGSAWS: evaluation protocol changes apparent performance, participant identity is recoverable, cross-user GRS prediction is weak, duration is a strong baseline, and confidence is unreliable.

Paper 2 must not be another JIGSAWS-only leaderboard or a repetition of the protocol gap. It must add two things:

1. **External scope:** determine whether identity-related shortcuts occur in additional public surgical-training datasets.
2. **Intervention:** actively reduce operator-identifying information and test whether this preserves or improves prediction for an unseen operator.

This creates a clean scientific distinction:

- **Paper 1 — diagnosis:** identity information is available and permissive validation can reward it.
- **Paper 2 — treatment and generalization:** identity suppression is an intervention; does it change shortcut performance and held-out-operator validity across datasets?

The second paper is publishable even if mitigation fails, provided the study is executed prospectively and the null is estimated precisely enough to be informative. A finding that identity suppression reduces apparent same-user performance but does not improve new-user performance would show that “remove identity” is not a sufficient solution.

## 1.2 Central question

> When repeated surgical performances from the same operators are available, how much predictive performance is attributable to operator-specific information, and does suppressing that information improve generalization to an unseen operator?

## 1.3 Central caution

“Identity is predictable” does not prove that a skill model uses identity. This paper must close that gap through interventions on the representation and formal permutation controls. Saliency maps, feature importance, and a separate identity classifier are supporting evidence only.

---

# 2. Target contribution and novelty

## 2.1 Intended contributions

1. A harmonized, leakage-resistant evaluation framework for repeated-measures surgical-skill datasets.
2. A formal identity-confounding audit using participant-level and record-level label permutations.
3. Direct representation interventions: removal of duration, linear identity-subspace removal, and adversarial identity suppression.
4. Paired evaluation under same-operator and held-out-operator protocols.
5. A multi-dataset account of the trade-off between retained task signal and recoverable identity.
6. Open code, manifests, processed feature schemas, prediction files, and analysis logs, subject to source-dataset redistribution rules.

## 2.2 What must not be claimed

Do not claim any of the following unless the completed evidence specifically supports it:

- that identity suppression necessarily improves surgical-skill assessment;
- that operator identity is inherently undesirable in personalized training;
- that the method has clinical validity or predicts patient outcomes;
- that a dataset-native objective metric is equivalent to expert-rated surgical skill;
- that the study is a systematic review;
- that any method is state of the art;
- that results generalize beyond the included datasets and modalities;
- that an adversarially trained representation contains no identity information;
- that failure of an identity probe proves absence of identity information.

## 2.3 Why the project is more novel than another accuracy paper

The literature already contains many JIGSAWS accuracy models, reports of LOSO/LOUO differences, calls for surgeon-invariant features, calibration/selective-prediction work, and general warnings about subject-wise evaluation. The unresolved step is causal and practical: intervene on the available identity signal, verify that the intervention worked with held-out probes, and determine whether new-user prediction improves. The project must be framed around that step, not around a new neural architecture.

---

# 3. Literature review

## 3.1 Review scope and limits

This is a targeted scoping review used to select the study design, current through **2026-09-21**. It used searches of accessible primary papers, PubMed/PMC, journal pages, arXiv/OpenReview where the primary version was available, official dataset pages, and official repositories. It is not PRISMA-compliant and must not be described in the manuscript as an exhaustive systematic review.

Before submission, update searches in PubMed, IEEE Xplore, Scopus or Web of Science, Google Scholar, and Crossref. Save exact query strings, dates, result counts, screening decisions, and a deduplicated bibliography in `docs/literature_search/`.

## 3.2 Foundational benchmark and validation literature

### JIGSAWS

Gao et al. introduced JIGSAWS as synchronized video and kinematics from eight operators performing suturing, knot tying, and needle passing. Ahmidi et al. subsequently documented the benchmark and its leave-one-user-out and leave-one-supertrial-out protocols. The official release confirms the small number of participants and repeated trials per participant.

- Official dataset: https://cirl.lcsr.jhu.edu/research/hmm/datasets/jigsaws_release/
- Benchmark paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC5559351/

The structural problem is that the self-declared novice/intermediate/expert label is constant within a participant. Under a split that places the same participant in training and testing, identifying the participant can retrieve the label without estimating trial-specific performance.

### Repeated-measures validation

Saeb et al. demonstrated that record-wise splitting can greatly underestimate error when repeated records from the same individual appear on both sides of a split. Little and Varoquaux emphasized an important counterpoint: a record-wise/subject-wise gap by itself does not uniquely establish identity confounding, because heterogeneous subject-wise splits may also produce underfitting or distribution mismatch.

- Saeb et al., *The need to approximate the use-case in clinical machine learning*: https://pmc.ncbi.nlm.nih.gov/articles/PMC5441397/
- Little et al., cross-validation perspectives: https://pmc.ncbi.nlm.nih.gov/articles/PMC5441396/

Consequently, this paper must not rely only on the protocol gap. It requires identity tests, permutation nulls, and representation interventions.

### Formal identity-confounding tests

Chaibub Neto et al. proposed subject-wise label permutations to quantify identity confounding in repeated-measures digital-health data. Keeping the shuffled label constant within participant destroys the genuine label association while leaving a record-wise model able to exploit participant recognition. A separate record-wise permutation destroys both structures and serves as a negative control.

- Primary article/PubMed: https://pubmed.ncbi.nlm.nih.gov/31633058/
- Full methodological preprint: https://arxiv.org/html/1712.03120v2

This framework should be implemented rather than approximated by a single shuffled-label run.

### Shortcut learning

Geirhos et al. describe shortcut learning as reliance on decision rules that succeed on standard benchmarks but fail under changed conditions. This provides the general conceptual framing, but “shortcut” should be used only where the alternative feature is easier, correlated with the target under the benchmark, and fails to support the intended deployment setting.

- https://www.nature.com/articles/s42256-020-00257-z

## 3.3 Surgical-skill assessment literature relevant to the gap

The surgical-skill literature contains:

- many JIGSAWS classification/regression studies;
- recurring performance deterioration under held-out-user evaluation;
- explanations involving individual style, dataset limitations, annotations, and weak external generalization;
- growing work on multimodal assessment, explainability, calibration, and selective prediction;
- little direct evidence that an identity-suppression intervention improves held-out-surgeon validity.

Key sources to retain and independently verify in the final bibliography include:

1. Ahmidi et al., JIGSAWS benchmark and evaluation methodology: https://pmc.ncbi.nlm.nih.gov/articles/PMC5559351/
2. Systematic review of deep neural networks for surgical skill assessment: https://arxiv.org/pdf/2103.05113
3. Review of machine learning for technical skill assessment: https://pmc.ncbi.nlm.nih.gov/articles/PMC8894462/
4. VBA-Net, including discussion of LOSO and LOUO and external pattern-cutting cohorts: https://pmc.ncbi.nlm.nih.gov/articles/PMC9852463/
5. Multimodal surgical-skill assessment: https://pmc.ncbi.nlm.nih.gov/articles/PMC9571767/
6. Recent calibration/trustworthiness work, showing that calibration and risk-coverage are no longer unoccupied novelty territory: https://link.springer.com/article/10.1007/s44443-026-00647-0
7. Recent work on transferable surgical-skill representations and cross-rubric transfer must be screened because it may overlap with representation-generalization claims: https://arxiv.org/html/2608.17519v1

The completed introduction must distinguish three questions:

1. Is the target a valid measure of skill?
2. Does the evaluation protocol estimate the intended deployment setting?
3. Does the fitted model rely on participant-specific information?

These questions are related but not interchangeable.

## 3.4 Identity-invariant representation literature

Domain-adversarial training uses a gradient-reversal objective to learn features predictive of the main task but uninformative about a domain label. Here, training-participant identity can be treated as the nuisance/domain label. The method is established; applying it is not itself the novelty.

- Ganin et al., *Domain-Adversarial Training of Neural Networks*: https://jmlr.org/papers/v17/15-239.html

Subject-invariant adversarial representations have also been studied in biosignals, including disentangled adversarial autoencoders. These papers establish feasibility but also caution that “confusing the training discriminator” is not proof of complete invariance.

- Disentangled adversarial autoencoder for subject-invariant physiological representations: https://pubmed.ncbi.nlm.nih.gov/33746496/

Therefore, every mitigation must be followed by a fresh identity probe that was not used as the adversary. The probe should include linear and nonlinear models.

## 3.5 Public dataset review

| Dataset | Public status | Participants/trials | Potential target | Role | Critical limitation |
|---|---|---:|---|---|---|
| JIGSAWS | Access-request public benchmark | 8 participants; approximately 101–103 usable trials depending on release/accounting | Trial-level modified OSATS/GRS; person-level experience class | Mandatory anchor dataset | Very small participant count; skill class is constant within participant |
| ROSMA | Public repository/release | 12 users; 206–207 trials | `scores.txt` and questionnaire exist, but score construction must be verified | Candidate external skill/performance dataset | May provide objective/task scores rather than expert-rated skill; target semantics unresolved |
| BGU-SKILLS | Public repository as of 2025 | 18 residents; 972 trials over six months | Longitudinal task metrics, shift/session, fatigue/activity data | Longitudinal external validation | No interchangeable GRS target; predicting kinematic metrics from the same kinematics may be circular |
| BGU-PatCut | Public, CC BY 4.0 | 54 participants; about 1,254 trials | Task stages, perturbation condition, repetition, performance variables | Large identity/robustness dataset | Primarily an adaptation/perturbation dataset, not necessarily expert-rated skill |
| DESK | Public research dataset | Platform/task dependent | Gesture/domain labels | Exclude from primary skill analysis | Designed mainly for robot/platform transfer and gesture classification, not human skill validity |
| MISTIC-SL | Historically not publicly available | — | Skill/activity labels | Exclude unless availability is independently confirmed | Primary publication stated it was not publicly available |

Primary links:

- ROSMA repository and schema: https://github.com/irivas-uma/rosma
- ROSMA paper: https://arxiv.org/abs/2102.03643
- BGU-SKILLS paper: https://arxiv.org/html/2503.21591v1
- BGU-SKILLS repository landing page: https://edmond.mpg.de/dataset.xhtml?persistentId=doi:10.17617/3.CYSIAP
- BGU-PatCut DOI landing page and CC BY 4.0 license: https://edmond.mpg.de/dataset.xhtml?persistentId=doi:10.17617/3.JK4ANF
- DESK paper: https://arxiv.org/abs/1903.00959

## 3.6 Literature-derived design decision

Do not assume that every dataset supplies a common “skill” outcome. The project is multi-dataset only if at least two datasets have:

1. stable participant identifiers;
2. repeated trials per participant;
3. an independently meaningful trial-level or participant-level performance/skill outcome;
4. enough metadata to construct participant-disjoint folds;
5. a license or data-use agreement permitting the proposed analysis;
6. no need to reconstruct the outcome directly from the same input variables in a tautological way.

JIGSAWS qualifies. ROSMA is a candidate pending inspection of `scores.txt`. BGU-SKILLS and BGU-PatCut qualify for identity and longitudinal/robustness analyses, but must not automatically be described as expert-rated skill datasets.

---

# 4. Feasibility gate: complete before modeling

Create `reports/feasibility_report.md` and stop before model development until all items below are resolved.

## 4.1 Dataset inventory

For every candidate dataset, record:

- official title, DOI, paper, repository, and exact version;
- access date and download method;
- license/data-use agreement;
- whether redistribution of raw or derived data is permitted;
- file counts, byte counts, and SHA-256 hashes;
- participant identifiers and number of participants;
- tasks, trials per participant/task, sessions, and missing trials;
- input modalities and sampling frequencies;
- outcome variables, units, direction, derivation, and rater provenance;
- whether outcomes vary within participant;
- whether duration or another feature is literally part of the outcome formula;
- missingness and exclusion requirements;
- any participant appearing under multiple identifiers;
- whether the source paper and deposited files agree.

## 4.2 Target validity decision table

For every proposed target answer:

1. Is it expert rated, self-declared, objectively measured, experimental condition, or derived from input data?
2. Does it vary within participant?
3. Is it partly calculated from duration, path length, motion, errors, or other planned predictors?
4. Would prediction be tautological?
5. Does higher always mean better?
6. Is it comparable across tasks or only within task?
7. What deployment interpretation, if any, is justified?

Do not proceed with a target merely because a file is named `scores.txt`.

## 4.3 Go/no-go rules

### Plan A: full multi-dataset skill/performance paper

Proceed if JIGSAWS plus at least one other dataset contains a defensible non-tautological performance target and participant IDs.

### Plan B: multi-dataset representation audit with one primary skill dataset

If only JIGSAWS has a defensible skill outcome, use JIGSAWS for the confirmatory skill intervention and other datasets only for identity-recoverability and longitudinal/perturbation robustness. The title, abstract, and claims must say so explicitly.

### Stop rule

If no additional dataset supports a meaningful complementary analysis, stop and issue a no-go report. Do not force a “multi-dataset skill paper” by relabeling repetition index, session number, perturbation condition, or duration as skill.

---

# 5. Study design

## 5.1 Unit of analysis

The observational unit is a complete task trial. The independent sampling unit for uncertainty is the participant. Windows, frames, gestures, or time points from a trial must never be divided across training and testing.

Primary analyses are task specific. Cross-task pooling is secondary and must include dataset and task indicators; do not imply a common measurement scale without a justified transformation.

## 5.2 Outcomes

### JIGSAWS primary outcome

Trial-level GRS/modified OSATS total, analyzed as a continuous outcome. Person-level novice/intermediate/expert classification is a secondary diagnostic because it is constant within participant and structurally admits identity lookup.

### External-dataset outcomes

Select only after the feasibility gate. Prefer, in order:

1. blinded expert-rated trial score;
2. independent error/accuracy outcome not calculated from planned predictors;
3. validated composite performance score with a fully documented formula;
4. dataset-native objective score, with explicit acknowledgement of construct limits.

Do not use completion time as both input and outcome in the same model. If an outcome formula contains duration, run a sensitivity outcome excluding the duration component where possible.

## 5.3 Inputs

Primary input is kinematics because it is available across the strongest candidate datasets and is computationally manageable for an independent researcher.

Use two feature families:

1. **Harmonized summary features:** duration, path length, mean/SD/quantiles of speed, acceleration and jerk, idle fraction, workspace volume or spread, bimanual coordination, left/right asymmetry, gripper activity, and economy-of-motion measures available across datasets.
2. **Sequence representation:** a compact temporal encoder operating on resampled kinematic sequences. Keep architecture intentionally modest.

No feature may use test-participant data to determine scaling, filtering thresholds, principal components, imputations, or feature selection.

## 5.4 Evaluation protocols

For every eligible dataset/task:

1. **Repeated-record/same-participant protocol:** source-defined repetition split where available; otherwise grouped-by-trial stratified folds that intentionally retain each participant on both sides. This measures performance when the system has already seen that operator.
2. **Held-out-participant protocol:** leave one participant out, or grouped K-fold when participant count makes leave-one-out computationally prohibitive. This estimates deployment to a new operator.
3. **Optional held-out-session protocol:** only where sessions exist and can be separated without participant leakage.

Never call the first protocol “external,” “independent,” or “unseen surgeon” validation.

## 5.5 Model families

Use a small predeclared set:

### Non-neural baselines

- training-fold mean/median reference;
- duration-only linear or ordinal model;
- ridge/elastic-net regression for continuous targets;
- multinomial logistic regression for categorical targets;
- optional gradient boosting only if added before outcomes are inspected.

### Sequence baseline

- one compact 1D CNN or GRU/TCN encoder;
- global pooling;
- linear outcome head;
- training-participant identity head where required.

Do not conduct an architecture tournament. The scientific variable is identity suppression, not network novelty.

## 5.6 Identity interventions

Evaluate the following in increasing complexity:

### I0: No suppression

Ordinary training using the predeclared feature set.

### I1: Remove direct duration

Exclude duration and any exact algebraic equivalent. This tests the simplest shortcut identified by paper 1.

### I2: Duration residualization

Within each training fold, regress each non-duration feature on duration using training data only. Apply the fitted transformation to validation/test data. This tests whether duration-associated variation drives results. Report both linear residualization and the direct-removal result.

### I3: Linear identity-subspace removal

Within each outer training fold:

1. standardize features using training data;
2. fit a regularized multinomial participant-ID classifier using nested participant-safe/repetition-safe validation;
3. construct the span of the fitted identity coefficient matrix;
4. remove projections onto the first `k` identity directions;
5. choose `k` using only inner-fold data based on the predeclared utility/invariance criterion;
6. apply the fixed projection to the outer test participant.

Implement unit tests proving that no outer-test records influence the projection.

### I4: Adversarial identity suppression

Use a gradient-reversal identity head. Optimize:

`L_total = L_task - lambda * L_identity`

where the implementation's gradient-reversal convention is documented so the sign is unambiguous. Predeclare a small lambda grid such as `{0, 0.01, 0.1, 0.3, 1.0}` and select within the inner loop. The identity head includes only participants present in the training fold.

### I5: Optional disentangled model

Only after I0–I4 work and only if compute permits. Separate shared/task and participant-specific latent components with reconstruction. Treat this as exploratory.

## 5.7 Fresh identity probes

After every intervention, freeze the representation and train new probes not used during representation learning:

- regularized multinomial logistic regression;
- nonlinear probe such as random forest or shallow MLP;
- duration-only identity probe;
- majority and empirical-chance references.

Probe evaluation must hold out repetitions/trials while retaining participant classes. Use nested tuning. Report macro accuracy, balanced accuracy, macro-F1, log loss, and chance appropriate to class balance.

A low linear-probe score is insufficient if a nonlinear probe still recovers identity.

---

# 6. Prespecified hypotheses and estimands

## H1: Protocol gap

Same-participant evaluation will yield more favorable task performance than held-out-participant evaluation.

**Estimand:** participant-averaged paired difference in the primary metric between protocols for the same model and feature set.

This replicates prior evidence and is not the main novelty.

## H2: Identity recoverability

Operator identity will be recoverable from unsuppressed kinematic representations above an empirical chance reference.

**Estimand:** probe performance minus the median participant-label permutation null.

## H3: Identity-confounding null

Under the same-participant protocol, participant-wise permutation of person-level labels will preserve more apparent predictive performance than record-wise permutation.

**Estimand:** difference between the medians of the two permutation distributions, with empirical tail probability.

For continuous outcomes that vary within participant, define a valid grouped permutation only after checking exchangeability. Do not mechanically apply a case/control permutation design to nonexchangeable longitudinal outcomes.

## H4: Intervention efficacy

Identity suppression will reduce identity-probe performance relative to the unsuppressed representation.

**Estimand:** paired participant- or permutation-level difference in probe metric.

## H5: New-user utility

Identity suppression may improve held-out-participant prediction, but this is genuinely uncertain.

**Primary estimand:** change in held-out-participant MAE for the primary continuous outcome, suppression minus unsuppressed. Negative values favor suppression.

The manuscript must report the full estimate and interval even if null or harmful.

## H6: Apparent same-user utility

For person-level skill classification, identity suppression is expected to reduce same-participant accuracy because it removes information that can retrieve the participant's constant label.

This is the strongest direct test of whether the classifier benefited from identity-compatible information.

## Primary endpoint hierarchy

1. Change in held-out-participant MAE under the strongest successfully verified suppression intervention versus I0, averaged within dataset/task and synthesized across eligible datasets.
2. Change in nonlinear identity-probe balanced accuracy.
3. Change in same-participant person-level skill accuracy on JIGSAWS.

All other endpoints are secondary or exploratory. Freeze this hierarchy before running final models.

---

# 7. Statistical analysis plan

## 7.1 Out-of-fold predictions

Every reported predictive result must derive from predictions made when the complete trial and, for held-out-participant analyses, the complete participant were absent from model fitting and preprocessing.

Save one row per prediction with:

- dataset/version;
- task;
- participant;
- session/trial;
- fold;
- intervention;
- model;
- seed;
- target;
- prediction;
- uncertainty/confidence if applicable;
- exclusion flags;
- git commit and configuration hash.

## 7.2 Hyperparameter tuning

Use nested validation. The inner loop must respect the intended generalization unit. For held-out-user evaluation, inner folds must also hold out complete users.

With very small participant counts, keep grids minimal. Do not select hyperparameters on outer-fold results or aggregate all outer predictions and tune retrospectively.

## 7.3 Uncertainty

The participant is the resampling unit.

Use:

- paired participant bootstrap intervals where enough participants exist;
- exact or Monte Carlo participant-level permutation tests where appropriate;
- report all participant-level estimates and leave-one-participant sensitivity analyses;
- do not use cross-validation fold standard deviation as a confidence interval;
- do not treat trials, frames, or windows as independent for inferential sample size.

For JIGSAWS, emphasize interval width and leave-one-participant sensitivity because eight participants cannot support precise population claims.

## 7.4 Across-dataset synthesis

Do not pool raw scores with different scales. Within each dataset/task, express the intervention effect as:

- raw paired MAE difference;
- MAE difference divided by the training-fold target SD;
- optionally relative improvement versus the feature-free reference.

Synthesize standardized effects with a random-effects meta-analysis only if at least three substantively compatible dataset/task estimates exist. Otherwise present a forest plot without a pooled grand effect.

Treat tasks within one dataset as correlated. Use dataset-clustered uncertainty or present task-specific estimates rather than pretending they are independent studies.

## 7.5 Multiple comparisons

One primary comparison is I4 versus I0 for held-out-user MAE, if I4 passes the identity-suppression verification. If I4 fails technically or does not reduce either identity probe, designate I3 versus I0 before inspecting task-performance outcomes.

Use Holm correction for the remaining confirmatory intervention comparisons. Label model/lambda/feature explorations explicitly exploratory.

## 7.6 Missing data and exclusions

Document all missing and malformed trials before viewing model results. Exclude only for predeclared reasons such as unreadable files, absent target, corrupted synchronization, or failure of a required signal. Do not remove statistical outliers merely because they harm performance.

Provide a flow table from deposited trials to analyzed trials for each dataset.

## 7.7 Equivalence/noninferiority

Do not claim that two methods are equivalent because a difference is nonsignificant. If claiming identity suppression preserves performance, predeclare a scientifically justified noninferiority margin. If no defensible margin exists, report estimates without an equivalence claim.

---

# 8. Leakage controls and unit tests

Implement automated tests for all of the following:

1. No participant overlap in held-out-participant folds.
2. No trial/window overlap across any fold.
3. No test data in scaling, imputation, filtering, PCA, residualization, feature selection, projection learning, or calibration.
4. Hyperparameter selection uses inner folds only.
5. Target columns and algebraic derivatives are absent from predictors.
6. Participant identifiers and filename tokens are absent from predictors.
7. Duration removal eliminates direct and duplicated duration columns.
8. Shuffled-target negative controls return chance/reference performance within Monte Carlo tolerance.
9. Identity-probe positive control can recover identity from an explicit one-hot participant feature.
10. Identical configurations reproduce identical predictions under fixed seeds.
11. Every final number is traceable to a prediction artifact and configuration hash.
12. Dataset-specific preprocessing does not use pooled information from another dataset's test fold.

Add a deliberate leakage canary during development: insert a participant code and verify that the audit detects it. Remove the canary from all final runs.

---

# 9. Negative and falsification controls

Required controls:

- record-wise label permutation;
- participant-wise label permutation where exchangeability permits;
- explicit participant one-hot identity lookup for person-level labels;
- duration-only model;
- feature-free mean/median predictor;
- shuffled identity labels for the identity head;
- random orthogonal projection removing the same number of dimensions as I3;
- capacity-matched model without gradient reversal for I4;
- probe on raw features and probe on suppressed features;
- task-label prediction or reconstruction check to ensure suppression has not erased all information.

The random-projection control is essential: improvement after I3 could result from generic regularization/dimensionality reduction rather than removal of identity specifically.

---

# 10. Reproducibility architecture

## 10.1 Repository layout

```text
project/
├── README.md
├── LICENSE
├── CITATION.cff
├── pyproject.toml
├── environment.lock.yml
├── configs/
│   ├── datasets/
│   ├── features/
│   ├── models/
│   └── experiments/
├── data/
│   ├── README.md
│   ├── raw/                 # gitignored; never redistribute restricted data
│   ├── manifests/
│   ├── interim/
│   └── processed/
├── docs/
│   ├── PROTOCOL.md
│   ├── DEVIATIONS.md
│   ├── DATA_DICTIONARY.md
│   ├── literature_search/
│   └── decisions/
├── src/
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── evaluation/
│   ├── statistics/
│   └── visualization/
├── tests/
├── scripts/
├── results/
│   ├── predictions/
│   ├── metrics/
│   ├── figures/
│   ├── tables/
│   └── logs/
├── reports/
│   ├── feasibility_report.md
│   ├── audit_report.md
│   └── final_results.md
└── paper/
    ├── manuscript.md
    ├── supplement.md
    ├── references.bib
    └── submission_checklist.md
```

## 10.2 Environment

Prefer Python 3.11+, `numpy`, `pandas`/`polars`, `scipy`, `scikit-learn`, `statsmodels`, `pytorch`, `hydra-core` or an equivalent explicit configuration system, `matplotlib`/`seaborn`, and `pytest`.

Pin exact versions. Log OS, Python, CUDA, device, package lock, and random seeds. CPU-compatible execution must exist for summary-feature models.

## 10.3 Data governance

- Do not commit raw datasets.
- Commit manifests, checksums, acquisition instructions, and permitted derived artifacts.
- Preserve source filenames only in private manifests if filenames expose participant IDs.
- Do not upload restricted data to model APIs.
- Jev or any proprietary model is not part of the primary project.
- If a source agreement forbids redistribution of derived features, release extraction code rather than features.

---

# 11. Implementation phases and acceptance criteria

## Phase 0: Protocol freeze

Deliver:

- `docs/PROTOCOL.md` copied from this specification and adapted only for verified dataset details;
- timestamped `docs/DEVIATIONS.md` initialized empty;
- literature search log;
- registered commit/tag `protocol-v1`.

Acceptance:

- hypotheses, primary endpoint, models, interventions, and exclusion rules are fixed before outcome inspection.

## Phase 1: Dataset feasibility

Deliver:

- `reports/feasibility_report.md`;
- data dictionaries;
- manifests and hashes;
- trial-count and missingness tables;
- target provenance diagrams/formulas;
- Plan A/Plan B/no-go decision.

Acceptance:

- at least two eligible analyses with defensible targets for Plan A, or explicit Plan B justification;
- all licenses and access requirements documented;
- no ambiguous `score` variable remains uninterpreted.

## Phase 2: Harmonized preprocessing

Deliver:

- deterministic loaders;
- common trial schema;
- feature extraction tests;
- dataset-level descriptive report;
- fold manifests committed before modeling.

Acceptance:

- re-running extraction yields identical hashes;
- held-out-user fold tests pass;
- sample counts reconcile with the source datasets.

## Phase 3: Baseline replication and audit

Deliver:

- feature-free and duration-only baselines;
- unsuppressed models;
- protocol-gap results;
- identity probes;
- formal permutation tests;
- leakage canary demonstration.

Acceptance:

- shuffled negative controls behave as expected;
- every metric is generated from saved out-of-fold predictions;
- paper 1's JIGSAWS findings are reproduced within documented tolerance or discrepancies are explained.

## Phase 4: Identity interventions

Deliver:

- I1–I4 implementations;
- random-projection and capacity controls;
- fresh linear and nonlinear probes;
- intervention-versus-baseline paired estimates;
- ablation log.

Acceptance:

- at least one intervention demonstrably reduces both linear and nonlinear identity recoverability, or the study reports that attempted suppression failed;
- no outer-test information enters intervention fitting;
- results are stable enough across seeds to interpret.

## Phase 5: Final locked analysis

Deliver:

- locked configuration list;
- final rerun from clean environment;
- prediction files;
- participant-level bootstrap/permutation outputs;
- figures/tables with machine-readable source data.

Acceptance:

- all tests pass;
- all reported values regenerate from one command;
- no undocumented deviations;
- rerun hashes match.

## Phase 6: Manuscript

Deliver:

- main manuscript;
- detailed supplement;
- data/code availability statement;
- reporting checklist appropriate to prediction-model and AI research;
- claim-evidence matrix;
- limitations section written before the conclusion.

Acceptance:

- every causal-sounding sentence is supported by an intervention or rewritten associationally;
- dataset-native scores are not called expert skill ratings unless they are;
- null results include intervals and detectable-effect discussion;
- paper 1 overlap is transparently disclosed and cited.

---

# 12. Required figures and tables

## Main figures

1. **Study schematic:** datasets, repeated trials, same-user versus held-out-user protocols, identity intervention, outcome and identity probes.
2. **Protocol gap forest plot:** paired standardized difference between same-user and held-out-user performance by dataset/task.
3. **Identity-confounding permutation plot:** observed performance, participant-wise permutation null, and record-wise permutation null.
4. **Utility–identity plane:** held-out-user task error versus nonlinear identity-probe performance for I0–I4 and random projection.
5. **Intervention forest plot:** paired change in held-out-user error for each intervention by dataset/task.
6. **JIGSAWS mechanistic panel:** same-user skill classification before/after suppression, identity lookup, and held-out-user result.

## Main tables

1. Dataset characteristics, target provenance, access/license, and included role.
2. Feature dictionary and cross-dataset availability.
3. Baseline and protocol results with participant-level intervals.
4. Identity-probe and permutation results.
5. Intervention effects and robustness controls.

## Supplement

- full fold composition;
- participant-level results;
- all hyperparameter grids and selections;
- all seeds;
- exclusions and missingness;
- sensitivity to outcome definition;
- leave-one-participant influence plots;
- duration removal/residualization details;
- random-projection controls;
- training curves and convergence failures;
- complete literature search update.

---

# 13. Manuscript outline

## Abstract

Use a structured Purpose/Methods/Results/Conclusion format if targeting IJCARS. Do not write numerical results until final locked analysis.

## Introduction

1. Automated skill assessment requires generalization to unseen operators.
2. Repeated-measures datasets allow identity shortcuts.
3. Protocol gaps and identity recoverability diagnose risk but do not prove model reliance.
4. Calls for “surgeon-invariant features” have not by themselves established that suppression helps.
5. State the multi-dataset intervention question and prespecified hypotheses.

## Related work

Separate:

- surgical-skill targets and their validity;
- evaluation protocols;
- identity confounding/permutation tests;
- invariant representation learning;
- public dataset limitations.

## Methods

Give enough detail to independently reproduce dataset inclusion, folds, features, models, permutation algorithms, probes, interventions, tuning, and participant-level inference.

## Results

Order results according to hypotheses, not visual impressiveness:

1. feasibility and target audit;
2. protocol gap;
3. identity recoverability and formal nulls;
4. intervention verification;
5. held-out-user utility;
6. negative controls and robustness.

Label any post-hoc work.

## Discussion

Address all possible result patterns:

- suppression reduces identity and improves new-user prediction;
- suppression reduces identity but does not improve prediction;
- suppression harms both same-user and new-user prediction;
- apparent suppression fools the adversary but not fresh probes;
- effects vary by dataset/task.

The last two patterns are scientifically important and must not be buried.

## Limitations

At minimum:

- few participants despite many trials;
- heterogeneous outcomes across datasets;
- simulation rather than clinical outcomes;
- participant identity can contain genuine stable skill information;
- removing identity may remove legitimate task signal;
- adversarial objectives do not guarantee invariance;
- public datasets differ in robot, task, sensors, preprocessing, and populations;
- no prospective clinical validation;
- any external-dataset score may be an imperfect skill construct.

---

# 14. Claims-to-evidence rules

| Potential claim | Minimum required evidence |
|---|---|
| Identity is present in the representation | Fresh identity probe above empirical permutation chance |
| Same-user performance is identity-confounded | Subject-wise label-permutation performance above record-wise permutation plus identity recoverability |
| The fitted model uses identity-compatible information | Performance changes after a targeted identity intervention beyond a dimension-matched random projection |
| Suppression works | Both linear and nonlinear fresh probes decline; task information is not globally erased |
| Suppression improves generalization | Paired held-out-user effect with participant-level interval favoring suppression |
| Suppression preserves performance | Predeclared noninferiority test or restrained descriptive language |
| Effect generalizes across datasets | Consistent estimates across at least two eligible datasets with compatible targets, not merely pooled trials |
| Clinical relevance | Not supportable from simulated public datasets alone |

---

# 15. Risks and fallback decisions

## Risk 1: ROSMA score is not a defensible skill target

Use ROSMA for identity recoverability and robustness only. Do not rename an objective task score as GRS.

## Risk 2: BGU-SKILLS data are too large or difficult to download

Begin with metadata and kinematics only. Do not download video unless needed. Preserve a resumable acquisition manifest.

## Risk 3: Dataset heterogeneity prevents a shared feature set

Use a small common feature core for cross-dataset figures and dataset-specific extended features as sensitivity analyses. Do not impute nonexistent sensor channels.

## Risk 4: Adversarial training is unstable

I3 linear subspace removal remains the primary mechanistic intervention. Report I4 failures transparently. Do not tune indefinitely on the test results.

## Risk 5: Suppression removes legitimate skill signal

This is a substantive result, not merely a technical failure. Analyze the utility–identity trade-off and discuss non-identifiability when skill is constant within person.

## Risk 6: Only JIGSAWS supports skill prediction

Adopt Plan B and frame other datasets as external tests of identity encoding. If that contribution is too weak after feasibility review, stop rather than publish an inflated claim.

## Risk 7: New overlapping paper appears

Repeat the literature search immediately before analysis lock and submission. Compare its datasets, intervention, validation protocol, and claims. Revise positioning, not results.

---

# 16. Exact initial instructions for Codex

Copy the following block into the coding environment together with this file:

> You are implementing a preregistration-style research project. Read `SECOND_PAPER_CODEX_MASTER_PLAN.md` completely before editing or downloading anything. First inspect the existing repository and paper-1 artifacts without changing them. Create a separate project directory or branch for paper 2. Execute only Phase 0 and Phase 1 initially. Do not train predictive models until `reports/feasibility_report.md` is complete and the Plan A/Plan B/no-go decision is explicit.
>
> Treat dataset documentation skeptically. Verify every target's construction from the deposited files and primary publication. Do not call repetition, session, duration, perturbation assignment, or a kinematics-derived formula “skill” without justification. Do not bypass access forms or licenses. Do not upload source data to external APIs.
>
> Reuse validated paper-1 code only through documented modules or copied commits; do not modify the submitted paper-1 analysis in place. Record reused functions, changes, and regression tests. Preserve an audit trail in `docs/DEVIATIONS.md` and `docs/decisions/`.
>
> At the end of Phase 1, return: (1) dataset availability and license table, (2) exact trial/participant/task counts, (3) outcome provenance table, (4) leakage and circularity risks, (5) compute/storage estimate, (6) recommended Plan A or Plan B, (7) any changes required to the prespecified analysis. Stop for human review after producing those materials.

After Phase 1 approval, instruct Codex:

> Implement Phases 2–4 with tests before final runs. Use participant-disjoint nested validation for all new-user claims. Save every out-of-fold prediction. Implement feature-free, duration-only, unsuppressed, duration-removed, duration-residualized, linear identity-subspace removal, and adversarial identity-suppression conditions, plus random-projection and capacity-matched controls. Use fresh linear and nonlinear identity probes. Implement participant-wise and record-wise permutations only where their exchangeability assumptions are defensible. If an assumption fails, stop that analysis and document why rather than improvising.
>
> Do not select methods from outer-test results. Do not report fold standard deviations as confidence intervals. Do not pool trials as independent observations. Generate a machine-readable provenance record for every table cell and figure point. Run all leakage tests before interpreting performance.

---

# 17. Definition of project completion

The project is complete only when:

1. At least one external public dataset has been verified and used in a scientifically defensible role, or a documented no-go decision explains why not.
2. All preprocessing and validation are participant safe.
3. Formal permutation controls distinguish identity confounding from a protocol gap alone where assumptions allow.
4. At least one targeted identity intervention and a dimension/capacity-matched control are implemented.
5. Fresh linear and nonlinear probes verify whether identity information changed.
6. Held-out-user effects have participant-level uncertainty.
7. All null, harmful, and heterogeneous results are reported.
8. Every result traces to saved out-of-fold predictions and a frozen configuration.
9. Raw restricted data are not redistributed.
10. The manuscript makes a narrower claim than the evidence, not a broader one.

---

# 18. Recommended immediate action

Do **not** begin by building the adversarial model. Begin by acquiring and auditing the metadata and smallest necessary files for ROSMA and BGU-SKILLS, especially `scores.txt`, questionnaires, data dictionaries, and license terms. The highest-value first result is a reliable answer to this question:

> Which public datasets actually contain a non-tautological, trial-level outcome that can support held-out-participant skill or performance prediction?

That answer determines whether the strongest paper is a true multi-dataset skill-intervention study or a more limited representation audit. Treating this gate seriously will prevent months of technically competent work on an invalid target.
