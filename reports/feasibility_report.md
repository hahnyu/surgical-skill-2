# Phase 1 dataset feasibility report

**Audit date:** 2026-09-21  
**Protocol:** `protocol-v1`  
**Decision:** **Plan A recommended; stop for human review before Phase 2**

## Decision

The project can proceed as a multi-dataset skill/performance study. JIGSAWS has
expert-rated trial GRS, BGU-PatCut has scan-derived cutting error independent of
the robot kinematics, and ROSMA has independently recorded task-error counts.
All three contain repeated trials and stable participant identities. These are
three defensible analyses and two distinct external performance targets.

BGU-SKILLS remains valuable for identity recoverability and longitudinal/shift
robustness, but not for primary performance prediction. Its published objective
metrics are calculated from the same kinematics that would be used as inputs.

The paper must distinguish constructs: JIGSAWS measures expert-rated surgical
skill; PatCut TE and ROSMA Errors measure task-specific objective performance.
The working title's “skill/performance” language is therefore required.

## 1. Availability, license, and integrity

| Dataset | Frozen source | Access | Terms | Files / bytes in deposit or local release | Phase 2 acquisition |
|---|---|---|---|---:|---|
| JIGSAWS | authorized local paper-1 copy; official research release | Application required | Academic research access; redistribution not established | 16,763 files / 893,368,730 bytes locally | Reuse ignored local link; do not copy or publish raw data. |
| ROSMA | Zenodo DOI 10.5281/zenodo.7100542 | Open | CC BY 4.0 | 413 / 22,207,164,939 | Download `scores.csv` plus 206 kinematic CSVs (~1.63 GB including the two small auxiliary CSVs); videos are unnecessary for the primary analysis. |
| BGU-SKILLS | DOI 10.17617/3.CYSIAP, v1.0 | Open | CC BY 4.0 | 22 / 270,172,633,854 | Download three kinematics archives (6,235,213,916 bytes) plus annotations/notes; omit video and tissue scans initially. |
| BGU-PatCut | DOI 10.17617/3.JK4ANF, v2.1 | Open | CC BY 4.0 | 55 / 408,314,079,634 | Use ZIP central-directory/range reads to extract accuracy tables and trial MAT files; do not download video/TIFF entries or whole participant archives by default. |

The normalized file manifests are in `data/manifests/`. For JIGSAWS, SHA-256
was computed for every local file. The exact path manifest is kept in the
Git-ignored `data/manifests/private/` because source filenames encode participant
IDs; the committed inventory provides grouped counts, bytes, and deterministic
tree hashes. The three public repositories provide MD5 checksums for remote
files. SHA-256 is marked `not_computed_remote_file` rather than fabricated;
Phase 2 will compute SHA-256 as each selected file is acquired. Source metadata
JSON is committed with its own SHA-256 manifest.

Sources: [JIGSAWS official page](https://cirl.lcsr.jhu.edu/research/hmm/datasets/jigsaws_release/),
[ROSMA Zenodo release](https://zenodo.org/records/7100542),
[BGU-SKILLS DOI](https://doi.org/10.17617/3.CYSIAP), and
[BGU-PatCut DOI](https://doi.org/10.17617/3.JK4ANF).

## 2. Exact participants, tasks, and trials

| Dataset/task or stratum | Participants | Planned or enumerated | Input trials | Target rows | Eligible primary pairs |
|---|---:|---:|---:|---:|---:|
| JIGSAWS Suturing | 8 | 40 | 40 | 39 | 39 |
| JIGSAWS Knot Tying | 8 | 40 | 40 | 36 | 36 |
| JIGSAWS Needle Passing | 7 | 40 | 40 | 28 | 28 |
| **JIGSAWS total** | **8 overall** | **120** | **120** | **103** | **103** |
| ROSMA Post and Sleeve | 12 | source does not define a fixed total | 65 | 65 | 65 |
| ROSMA Pea on a Peg | 12 | source does not define a fixed total | 71 | 71 | 71 |
| ROSMA Wire Chaser I | 12 | source does not define a fixed total | 70 | 71 | 70 |
| **ROSMA total** | **12** | — | **206** | **207** | **206** |
| BGU-SKILLS Knot Tying | 18 | 324 | 324 enumerated | no independent target | 311 source-paper identity rows |
| BGU-SKILLS Ring Tower Transfer | 18 | 324 | 324 enumerated | no independent target | 312 source-paper identity rows |
| BGU-SKILLS Suturing | 18 | 324 | 324 enumerated | no independent target | 315 source-paper identity rows |
| **BGU-SKILLS total** | **18** | **972** | **972 enumerated** | — | **938 source-paper identity rows** |
| BGU-PatCut force perturbations | 30 | 720 | 700 | 700 documented | 700 |
| BGU-PatCut motion perturbations | 24 | 576 | 554 | 554 documented | 554 |
| **BGU-PatCut total** | **54** | **1,296** | **1,254** | **1,254 documented** | **1,254** |

JIGSAWS has 40 kinematic files for each task, but its validated metadata and
transcriptions define 39/36/28 usable trials. Every usable GRS equals the sum of
the six expert-rating elements. All represented participant/task groups show
within-participant GRS variation. Only Suturing supplies official SkillDetection
split files in the local release; same-participant Knot Tying and Needle Passing
folds must be generated deterministically by the protocol.

ROSMA's current deposit contains 206 kinematic trial CSVs and 204 videos. The
source paper describes 206 data files and 206 videos, so the two missing current
videos are a source/deposit mismatch. They do not affect the kinematics-only
analysis. `scores.csv` has one extra Wire Chaser target with no kinematics.

BGU-SKILLS enrolled 21 residents and documents three withdrawals (H, R, S),
leaving 18 participants × 6 shifts × 3 sessions × 3 tasks = 972 trial keys.
The source analysis flags 34 exclusions and uses 938 trials. Phase 2 will retain
both an all-readable identity audit and a source-analysis-cohort sensitivity;
source exclusions will not silently replace deposited availability.

BGU-PatCut documents 30 force and 24 motion participants, each scheduled for 24
trials. Its explicit missing-trial lists contain 20 and 22 absent trials,
respectively, yielding 1,254. The manual states that each participant archive
contains a trial-indexed `AccuracyResults.mat`; a range-read pilot confirmed the
file and MATLAB table header in one archive without downloading the 4.08 GB ZIP.

Machine-readable counts and missingness are in
`reports/tables/trial_counts.csv` and `reports/tables/missingness.csv`.

## 3. Outcome provenance and eligibility

| Dataset | Candidate | Provenance | Within participant? | Predictor circularity | Decision |
|---|---|---|---|---|---|
| JIGSAWS | GRS | Sum of six expert modified-OSATS ratings | Yes | No direct algebraic overlap | **Primary skill outcome** |
| JIGSAWS | novice/intermediate/expert | Self-declared person label | No | Participant identity can retrieve label | Secondary mechanistic diagnostic |
| ROSMA | Errors | Observed task-specific error/drop count | Yes | Not computed from robot channels | **Primary objective performance outcome** |
| ROSMA | Time | Completion duration | Yes | Equal to information available from record length/timestamps | Exclude as primary target |
| ROSMA | Score | Time + 15×Errors, or Time + 10×Errors for Wire Chaser | Yes | Contains duration | Exclude as primary target |
| BGU-SKILLS | time/path/orientation metrics | Calculated from task windows and kinematics | Yes | Direct transformations of inputs | No performance target; identity audit only |
| BGU-PatCut | TE | Pixel error from post-trial gauze scan; `Eoutside + Einside` | Yes | Scan is independent of kinematics | **Primary objective performance outcome** |
| BGU-PatCut | TT | First tool closure to final cut | Yes | Duration-derived | Exclude as primary target |
| BGU-PatCut | CET | `z(TT) + z(TE)` in source study | Yes | Contains duration and source-global moments | Exclude |

The full diagram, formulas, and anomaly notes are in
`docs/TARGET_PROVENANCE.md`; field definitions are in
`docs/DATA_DICTIONARY.md`.

ROSMA's ambiguous `Score` is resolved rather than ignored. The published
penalty formula explains its intended meaning. Row `X11_Pea_on_a_Peg_01`
appears to omit a decimal factor of 1000 in both time and score, and
`X11_Pea_on_a_Peg_04` applies one 15-second penalty despite two recorded errors.
The primary `Errors` values are not algebraically affected by either composite
anomaly. The composite remains excluded unless the data authors clarify it.

BGU-PatCut's TE is the strongest external target: accuracy comes from a separate
image of the cut gauze, and its components have an explicit physical meaning.
MATLAB v5 stores the deposited table as a proprietary MATLAB table object;
generic SciPy reads it as opaque. Phase 2 therefore requires MATLAB/Octave or a
tested table decoder/export step before the loader can pass acceptance tests.

## 4. Leakage, circularity, and construct risks

| Risk | Affected data | Consequence | Required control |
|---|---|---|---|
| Participant overlap | All | Same-person records can make identity useful and inflate deployment claims. | Complete participant holdout in outer and inner held-out-person folds. |
| Trial fragmentation | All | Frames/windows from one trial can cross folds. | Split complete trials before any windowing. |
| Fold-global preprocessing | All | Scaling, imputation, PCA, residualization, or identity projection can see the test person. | Fit every transform inside each training fold. |
| Constant person label | JIGSAWS skill class | Identity lookup predicts self-declared class without trial skill estimation. | Treat as secondary H6 diagnostic; use continuous GRS for primary skill modeling. |
| Duration in target | ROSMA Score; PatCut CET/TT | Near-tautological prediction from record length. | Exclude these targets; retain Errors and TE. |
| Global composite moments | PatCut CET | Published z-scores use information outside a training fold. | Do not reuse CET; if explored, recompute moments within folds and label exploratory. |
| Stage/condition/repetition | PatCut and BGU-SKILLS | Learning or perturbation schedule can be mistaken for skill. | Do not use these as primary predictors or labels; stratify folds and report stage/condition sensitivity. |
| Shift/session context | BGU-SKILLS | Identity or fatigue proxies can dominate longitudinal comparison. | Report identity recovery by session/shift and optional held-out-session analysis; do not call it skill. |
| Source exclusions | BGU-SKILLS | Outcome- or quality-informed filtering can alter identity estimates. | Reproduce documented flags and compare readable-all versus source-paper cohorts. |
| Identifier exposure | All | Filenames can leak participant identity into features or logs. | Parse IDs only into grouping keys; never expose source filename tokens to models. |
| Probe underpower/linearity | All | Failed linear probe can falsely imply invariance. | Fresh nested linear and nonlinear probes plus empirical permutation chance. |

Additional design issue: ROSMA Errors is a sparse count. Nonzero errors occur in
14/65 Post and Sleeve, 30/71 Pea on a Peg, and 17/70 Wire Chaser trials, totaling
61/206. Primary MAE and the frozen ridge baseline remain valid for the
prespecified common endpoint, but task-specific zero rates and error
distributions must accompany MAE. No count-model family will be added after
outcome inspection without a deviation.

## 5. Compute and storage estimate

Full acquisition of the three public deposits would require 700,693,878,427
bytes (~700.7 GB decimal) before working copies, which is unnecessary.

The minimum planned acquisition is:

- ROSMA: ~1.63 GB for kinematic CSVs plus negligible scores metadata.
- BGU-SKILLS: 6.24 GB for three kinematic archives plus small annotations.
- BGU-PatCut: outcome tables require well under 10 MB using central-directory
  and HTTP range reads. Selectively extracting 1,254 trial MAT entries is
  provisionally estimated at 9–15 GB from one inspected archive; Phase 2 must
  benchmark five archives before committing to the full extraction.
- JIGSAWS: 0.89 GB already present through the local read-only link.

A 35 GB free-space budget should cover the initial kinematics-only acquisition,
checksummed raw files, harmonized features, and intermediate caches if archives
are streamed and videos/scans are not retained. Keep 50 GB available until the
PatCut five-archive benchmark narrows the estimate.

Summary feature extraction and linear nested models should fit on a modern
8–16-core workstation with 32 GB RAM. The compact sequence model and adversarial
grid should fit on one 16–24 GB GPU. A preliminary planning envelope is 50–150
GPU-hours and 100–300 CPU-hours for all folds, interventions, probes, and
permutations. Phase 2 must run a one-task benchmark and update this estimate
before Phase 3; this is an operational estimate, not a commitment to exhaust a
compute budget.

## 6. Plan A analysis roles

| Dataset | Confirmatory outcome role | Identity role | Generalization unit |
|---|---|---|---|
| JIGSAWS | Expert-rated GRS; H6 person-level class diagnostic | Primary mechanistic anchor | Held-out operator and same-operator repetitions |
| ROSMA | Task-specific Errors | External identity suppression test | Held-out participant; same-participant repetitions |
| BGU-PatCut | Scan-derived TE; Eoutside/Einside sensitivities | Largest external intervention test | Held-out participant; same-participant trials stratified by experiment/stage/condition |
| BGU-SKILLS | None | External longitudinal identity and session robustness | Held-out participant; optional held-out session |

The primary endpoint hierarchy remains unchanged. Eligible targets are analyzed
on their native task scales, and each intervention effect is a within-task
paired change in held-out-participant MAE before synthesis. A dataset with more
trials does not automatically dominate the meta-analysis.

## 7. Prespecified-analysis refinements required by feasibility

These are conditional choices already allowed by the protocol's Phase 1 gate:

1. Set BGU-PatCut TE as the primary external performance target and ROSMA Errors
   as a second external performance target. Retain JIGSAWS GRS as the skill
   anchor.
2. Restrict BGU-SKILLS to identity recoverability, longitudinal robustness, and
   optional held-out-session analysis. Do not derive a tissue-scan accuracy
   target during the confirmatory study.
3. Exclude ROSMA Score/Time and PatCut TT/CET from primary target analyses.
4. For PatCut, stratify fold construction and reporting by experiment,
   perturbation assignment, and baseline/training/post stage. Do not provide
   these variables to the primary kinematics-only predictor. Report TE
   components as sensitivity outcomes.
5. For ROSMA, model tasks separately and report the zero-error frequency. Keep
   the prespecified MAE/ridge analysis for comparability; any count or hurdle
   model would require a prospective deviation before model-result inspection.
6. Add a Phase 2 acquisition gate: validate PatCut table decoding, benchmark
   range extraction across five archives, and verify every selected download
   against repository MD5 plus locally computed SHA-256.
7. Keep official JIGSAWS Suturing splits where they match the intended protocol;
   generate and serialize deterministic same-participant folds for the other
   tasks. All held-out-participant folds are regenerated from participant keys.

No changes are proposed to H1–H6, the primary endpoint hierarchy, I0–I4, the
fixed baseline model families, participant-level uncertainty, or the rule that
all preprocessing occurs within folds.

## Gate checklist

- [x] More than two eligible analyses with defensible targets.
- [x] Participant IDs and repeated complete trials documented.
- [x] Access and license terms documented for every dataset.
- [x] File counts, byte counts, repository checksums, and local JIGSAWS SHA-256
  inventory recorded.
- [x] Trial counts and missingness reconciled with source documentation.
- [x] Every score/metric has a provenance and circularity decision.
- [x] Plan A role declared for each dataset.
- [x] No predictive model trained and no intervention result inspected.
- [ ] Human approval to begin Phase 2.
