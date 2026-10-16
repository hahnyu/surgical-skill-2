# IJCARS submission metadata

**Journal:** International Journal of Computer Assisted Radiology and Surgery
**Article type:** Original Article
**Title:** Operator identity and out-of-user generalization in automated surgical skill assessment: a multi-dataset evaluation
**Running title:** Operator identity in surgical skill assessment
**Total word count:** 4,245, including title, author details, abstract, references, figure captions, and tables

## Authors

1. Hamilton Jeong — College of Agriculture and Life Sciences, Cornell University
2. Zaid Elnasser — College of Agriculture and Life Sciences, Cornell University
3. Laurienne Jeong — College of Agriculture and Life Sciences, Cornell University
4. Bhumika Iroji — College of Engineering, Cornell University
5. Suélia de Siqueira Rodrigues Fleury Rosa — Meinig School of Biomedical Engineering, Cornell University

**Corresponding author:** Hamilton Jeong, hhj22@cornell.edu
**Corresponding address:** College of Agriculture and Life Sciences, Cornell University, 215 Garden Avenue, Ithaca, NY 14850, USA

## Abstract

**Purpose:** Repeated recordings from the same operator can permit surgical-performance models to use operator-specific motion patterns. We tested whether operator identity was recoverable from surgical kinematics and whether suppressing that information improved prediction for unseen operators.

**Methods:** We retrospectively analyzed 2,501 dry-lab trials representing 92 dataset-participants from JIGSAWS, ROSMA, BGU-PatCut, and BGU-SKILLS. Outcomes were expert-rated Global Rating Scale, observed task errors, and image-derived cutting error; BGU-SKILLS contributed to identity analysis only. We compared same-participant with held-out-participant evaluation, used fresh linear and random-forest identity probes and JIGSAWS label permutations, and evaluated duration removal, duration residualization, linear identity-subspace projection (I3), and adversarial suppression (I4). Intervals used 2,000 participant bootstrap replicates.

**Results:** Unsuppressed identity accuracy exceeded its record-wise permutation null in all ten dataset-task groups (linear 0.228–0.944; nonlinear 0.381–0.844; each empirical p=0.0196). JIGSAWS participant-wise permutations retained substantially more same-participant skill accuracy than record-wise permutations (median differences 0.444–0.538; each p=0.004975). I3 reduced fresh linear identity accuracy by 0.184 (95% interval 0.151–0.215) and nonlinear accuracy by 0.138 (0.098–0.175); I4 failed the prespecified two-probe rule. Held-out-participant standardized mean absolute error favored I3 in one of seven tasks and the unsuppressed model in six; six intervals crossed zero.

**Conclusion:** Identity was recoverable and targeted projection reduced tested identity recovery, but suppression did not consistently improve unseen-operator prediction. Identity diagnostics and held-out-user utility should be evaluated separately.

## Keywords

surgical skill assessment; operator identity; out-of-user validation; domain generalization; kinematics; representation learning

## Declarations for portal entry

**Funding:** The authors received no funding for this work.

**Competing interests:** The authors declare no financial or non-financial competing interests.

**Ethics:** This study was a secondary analysis of previously collected, de-identified research datasets. The investigators had no direct identifiers, no access to any re-identification key, and no interaction or intervention with participants. Under Cornell University guidance for research involving existing or secondary de-identified data, this activity does not constitute federally regulated human-participant research and did not require further Cornell Institutional Review Board review. The original dataset investigators were responsible for the ethics approvals and consent procedures applicable to the source studies.

**Consent:** Not applicable. No participants were recruited or contacted, and no identifiable information is reported.

**Data and code:** Analysis code, configurations, aggregate metrics, participant-opaque fold manifests, figures, tables, and artifact hashes are available at https://github.com/hahnyu/surgical-skill-2. JIGSAWS is available from its custodians under an academic research agreement and is not redistributed. ROSMA, BGU-SKILLS, and BGU-PatCut are available from their cited repositories under CC BY 4.0. Participant-level predictions remain local because source access terms differ.

## Upload map

1. Main editable source: `manuscript.tex`, `references.bib`, and `figures/Fig1.pdf` through `Fig6.pdf`
2. Main review PDF: `output/pdf/ijcars_manuscript.pdf`
3. Supplementary Information / Online Resource 1: `output/pdf/ESM_1.pdf`
4. Cover letter: `output/pdf/ijcars_cover_letter.pdf`

The AI-use disclosure remains intentionally reserved for the human authors in `ai_use_disclosure_PLACEHOLDER.md` and in the highlighted manuscript box.
