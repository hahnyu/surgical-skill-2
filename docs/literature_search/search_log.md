# Targeted literature and dataset search log

**Search date:** 2026-09-21  
**Scope:** feasibility sources for Phases 0–1; this is a targeted scoping search,
not a systematic review.

Searches used the open web, official dataset repositories, DOI landing pages,
primary papers, and the existing paper-1 repository. Search result counts were
not stable or consistently exposed by the search interface and are recorded as
`not available`; candidate sources actually screened are listed below.

| Query or direct lookup | Result count | Screening decision |
|---|---:|---|
| `JIGSAWS official dataset license access request trial counts data files` | not available | Retain official JHU page and access form; use existing authorized copy for file audit. |
| `ROSMA dataset official repository scores.txt GitHub irivas-uma rosma license` | not available | Retain official GitHub repository, Zenodo release, and primary paper. |
| `BGU-SKILLS dataset official repository DOI 10.17617/3.CYSIAP files license` | not available | Retain DOI/Edmond record, dataset manual, annotations, notes, and primary paper. |
| `site:arxiv.org BGU-SKILLS dataset analysis surgical skill` | not available | Retain arXiv 2503.21591 as the primary dataset paper. |
| `BGU-PatCut dataset official DOI 10.17617/3.JK4ANF files license` | not available | Retain DOI/Edmond record, dataset manual, and primary paper. |
| `\"Augmenting Robot-Assisted Pattern Cutting with Periodic Perturbations\" pdf` | not available | Retain IEEE DOI 10.1109/TBME.2024.3450702 and accessible author copy. |

## Sources retained for feasibility decisions

| Dataset/topic | Primary source | Role |
|---|---|---|
| JIGSAWS | https://cirl.lcsr.jhu.edu/research/hmm/datasets/jigsaws_release/ | Access terms, modalities, participants, tasks. |
| JIGSAWS benchmark | https://pmc.ncbi.nlm.nih.gov/articles/PMC5559351/ | Benchmark design and evaluation context. |
| ROSMA | https://zenodo.org/records/7100542 | Current deposited files, license, sizes, checksums. |
| ROSMA code/docs | https://github.com/irivas-uma/rosma | Variable definitions and repository documentation. |
| ROSMA paper | https://arxiv.org/abs/2102.03643 | Score formula, task errors, trial design. |
| BGU-SKILLS | https://doi.org/10.17617/3.CYSIAP | Deposited files, license, checksums, manual. |
| BGU-SKILLS paper | https://arxiv.org/abs/2503.21591 | Cohort, sampling, exclusions, performance metrics. |
| BGU-PatCut | https://doi.org/10.17617/3.JK4ANF | Deposited files, license, checksums, manual. |
| BGU-PatCut paper | https://doi.org/10.1109/TBME.2024.3450702 | Trial design, error and composite formulas. |

## Screening rule

A dataset advanced when it had repeated complete trials, stable participant IDs,
kinematics, sufficient provenance to count trials and missingness, and a license
or access route compatible with independent research. A target advanced to the
primary performance analysis only when it varied at trial level and was not an
algebraic restatement of the planned kinematic predictors.

## Analysis-lock update: 2026-09-26

The search was repeated immediately before the Phase 5 analysis lock, as
required by Risk 7 of the protocol. Searches covered PubMed, arXiv, IEEE, and
Springer using combinations of `surgical skill assessment`, `JIGSAWS`,
`ROSMA`, `unseen surgeon`, `operator identity`, `domain generalization`, and
`identity invariant representation`, restricted to 2024–2026 where the
interface permitted. Result counts were not consistently exposed.

| Source screened | Relevance and lock decision |
|---|---|
| [Multimodal learning for automated robotic surgical skill assessment](https://pubmed.ncbi.nlm.nih.gov/41399175/) (2025) | Directly overlaps JIGSAWS and ROSMA and combines video and kinematics. Retain for the manuscript comparison; the indexed abstract reports skill classification performance but does not describe the paired identity-suppression intervention and participant-level inference used here. |
| [OSS: Open Suturing Skills Vision-Based Assessment Challenge 2024–2025](https://arxiv.org/abs/2605.22200) (2026) | New open-surgery benchmark with skill classification, OSATS prediction, and tracking. Retain as a current benchmark and as evidence that fine-grained score prediction remains difficult. It does not displace this study's repeated-participant identity-confounding question. |
| [Generalized Recognition of Basic Surgical Actions Enables Skill Assessment and Vision-Language-Model-based Surgical Planning](https://arxiv.org/abs/2603.12787) (2026) | New multi-specialty action-recognition foundation model with a downstream skill application. Retain for breadth/generalization context; no matching operator-identity intervention was identified in the abstract. |
| [AI-Based Markerless Computer Vision Framework for Open Surgery Skill Assessment](https://pubmed.ncbi.nlm.nih.gov/42132409/) (2026) | Small prototype connecting markerless hand kinematics with expert ratings. Retain for construct-validity context; it does not test repeated-operator identity suppression. |

No directly overlapping paper was identified that combines the same-versus-held
participant protocol gap, fresh identity probes, participant-wise versus
record-wise permutation, and a targeted identity intervention across the
included public datasets. The search therefore changes the manuscript context,
not the locked analysis or its claims.
