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

