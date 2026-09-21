# Phase 1 data dictionary

This dictionary describes fields required for the planned harmonized trial
table. It records source semantics rather than asserting that heterogeneous
outcomes share one scale.

## Common trial schema planned for Phase 2

| Field | Type | Meaning |
|---|---|---|
| `dataset` | categorical | Source dataset and frozen version. |
| `task` | categorical | Dataset-native task; primary models are task specific. |
| `participant_id_private` | string | Source participant ID, retained only in restricted/local artifacts. |
| `participant_key` | string | Dataset-scoped pseudonymous key for analysis outputs. |
| `trial_id_private` | string | Source trial/file ID, retained only when redistribution permits. |
| `trial_key` | string | Stable dataset-scoped pseudonymous trial key. |
| `repetition` | integer | Dataset-native repetition/trial number; design variable, never a skill label. |
| `session` | categorical | Session/shift/stage where present; never a skill label. |
| `condition` | categorical | Experimental condition where present; used for stratification/sensitivity, not as a primary predictor. |
| `sampling_hz` | numeric | Nominal or timestamp-derived kinematic sampling rate. |
| `n_samples` | integer | Samples in the complete, valid task window. |
| `duration_s` | numeric | Task-window duration; excluded by I1 and from any model whose target formula contains time. |
| `outcome_name` | categorical | Dataset-native eligible outcome. |
| `outcome_value` | numeric | Untransformed trial-level target. |
| `outcome_direction` | categorical | `higher_better` or `lower_better`. |
| `valid_input` | boolean | Required kinematics are readable and match the trial. |
| `valid_target` | boolean | Required target is present and provenance is resolved. |
| `exclusion_reason` | string/null | Source-defined or protocol-defined exclusion, never inferred from target extremity alone. |

## JIGSAWS

| Source field | Unit/type | Provenance and use |
|---|---|---|
| task | Suturing, Knot Tying, Needle Passing | Parsed from source trial identity. |
| subject | B–I | Eight operators overall; Needle Passing has seven represented operators. |
| repetition | 1–5 nominal | Repeated complete trial. |
| self-declared skill | novice/intermediate/expert | Constant within operator; secondary identity-compatible diagnostic only. |
| six modified-OSATS elements | ordinal, nominally 1–5 each | Expert ratings: respect for tissue, needle handling, time and motion, flow, overall performance, final-product quality. Individual order requires source-paper confirmation before element-level reporting. |
| GRS | 6–30, higher better | Exact sum of the six elements in all 103 usable trials; primary JIGSAWS outcome. |
| kinematics | 76 channels at 30 Hz | Four 19-channel arm blocks: MTML, MTMR, PSM1, PSM2; each has position (3), orientation matrix (9), linear velocity (3), angular velocity (3), and gripper angle (1). |
| gesture window | frame indices | First annotated gesture start through final annotated gesture end, inclusive. |

## ROSMA, Zenodo record 7100542

| Source field | Unit/type | Provenance and use |
|---|---|---|
| `File_name` | trial identifier | Encodes participant X01–X12, task, and repetition. |
| `Time` | seconds | Dataset table and paper; lower better. Not an eligible primary target when duration-derived predictors are used. |
| `Errors` | nonnegative count | Task-defined dropped/error events recorded independently of kinematic channels; lower better. Primary ROSMA target. |
| `Score` | seconds plus penalty | `Time + 15×Errors` for Post and Sleeve / Pea on a Peg; `Time + 10×Errors` for Wire Chaser I. Excluded from primary prediction because duration is algebraically embedded. |
| kinematics | 160 variables at 50 Hz | dVRK kinematics documented by the source repository; exact channel names will be asserted from downloaded headers in Phase 2. |
| questionnaire | participant-level survey | Context only; not a trial performance target. |

## BGU-SKILLS, version 1.0

| Source field | Unit/type | Provenance and use |
|---|---|---|
| participant | A–U excluding H, R, S | 18 residents who completed the longitudinal protocol. |
| shift | 1–6 | Monthly 26-hour shift cycle; design variable. |
| session | a/b/c | Before, during, and after the shift; design variable. |
| task | Ring Tower Transfer, Knot Tying, Suturing | One trial per task per session. |
| timestamps/time/video time | time | Synchronization and elapsed time. |
| kinematics | timestamped dVRK channels | PSM1/PSM2/MTMR/MTML position, orientation, velocity, wrench, and gripper or jaw. Primary identity/robustness input. |
| completion time | seconds | Derived from task boundaries; not an independent target for this kinematics study. |
| path length | distance | Derived from the same kinematics; ineligible as a prediction target. |
| orientation-change rate | rate | Derived from the same kinematics; ineligible as a prediction target. |
| tissue scans | images, Suturing only | Deposited without a validated trial-level accuracy score; future outcome derivation would require a separate preregistered validation study. |

## BGU-PatCut, version 2.1

| Source field | Unit/type | Provenance and use |
|---|---|---|
| participant | eight-digit source ID | 30 force-perturbation and 24 motion-perturbation participants. Private identifier. |
| condition | control/experimental | Between-participant perturbation assignment. |
| trial | 1–24 | Baseline 1–5, training 6–15, post/transfer 16–24; design variable. |
| `TE` | pixel area/count, lower better | Total cutting error measured from an independent scanned gauze image; primary PatCut target. |
| `Eoutside` | pixel area/count | Cut area outside the target boundary; component/sensitivity outcome. |
| `Einside` | pixel area/count | Uncut area inside the target boundary; component/sensitivity outcome. |
| task time (`TT`) | seconds | First tool closure to final cut; duration-derived and not a primary target. |
| composite error/time (`CET`) | standardized sum | `z(TT) + z(TE)` using source-study aggregate moments. Excluded because it contains duration and global standardization would leak evaluation data if reused. |
| dVRK trial data | MATLAB struct | MTMR, MTML, PSM1, PSM2 position/orientation/velocity/wrench and gripper/jaw, plus video timestamps. |
| segmentation | MATLAB table | Segment start timestamps per trial. |
| gauze scan/video | TIFF/AVI | Independent accuracy source and synchronized recording. |

