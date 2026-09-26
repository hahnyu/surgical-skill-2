# Adapted TRIPOD+AI reporting checklist

This checklist maps the 27 main TRIPOD+AI items and 52 subitems to the manuscript package [@Collins2024]. TRIPOD+AI was written for clinical prediction models; this study is a retrospective dry-lab benchmark and mechanistic intervention analysis. “N/A” is used where the item does not apply. Page numbers should be added after journal typesetting.

| Item | Requirement | Location/status |
|---|---|---|
| 1 | Identify the study as development/evaluation of a prediction model, model type, target population, and outcome | Title and Abstract. Multi-dataset evaluation; ridge/logistic/MLP models; surgical-training operators; task-specific outcomes. |
| 2 | Structured abstract using TRIPOD+AI for Abstracts | Abstract: Purpose, Methods, Results, Conclusion; detailed 13-item mapping below. |
| 3a | Medical/technical context and rationale | Introduction ¶1–3. |
| 3b | Target population and care pathway or setting | Introduction; Methods—Datasets. Dry-lab surgical-training tasks, not a clinical care pathway. |
| 3c | Intended purpose, users, role, and health inequalities | Introduction and Discussion. Intended methodological audit for researchers; no clinical use; demographic inequality could not be assessed. |
| 4 | Study objectives, including development/evaluation | Final Introduction paragraph; prespecified H1–H6 in `docs/PROTOCOL.md`. |
| 5a | Data sources and study design, separately for development/evaluation data | Methods—Study design and Datasets; Supplement S2. Same datasets supply nested training and out-of-fold evaluation. |
| 5b | Key dates | Protocol freeze date reported; source release/version identifiers reported. Original participant collection dates should be taken from source papers if required by the journal. |
| 6a | Study settings | Methods—Datasets; Supplement S2. |
| 6b | Eligibility criteria | Methods—Datasets; Supplement S2 and S3. |
| 6c | Treatments received | N/A for retrospective task-performance prediction. Perturbation conditions existed in PatCut but were not predictors. |
| 7 | Data preparation | Methods—Kinematic preprocessing; Supplement S4. |
| 8a | Outcome definition and timing | Methods—Datasets; Supplement S3; `docs/TARGET_PROVENANCE.md`. |
| 8b | Outcome assessors and measurement | Supplement S2–S3; source publications. JIGSAWS expert ratings, ROSMA observed errors, PatCut image-derived error. |
| 8c | Blinding of outcome assessment to predictors | Source-specific and not fully documented in the analysis record; flag for source-paper confirmation before submission. |
| 9a | Candidate and final predictors | Methods—Kinematic preprocessing; `phase5_table2_features.csv`. |
| 9b | Predictor measurement | Methods—Kinematic preprocessing; Supplement S4. |
| 9c | Blinding of predictor assessment to outcome | Features were deterministically extracted from kinematics; outcome columns were not used in extraction. Source data collectors’ blinding is not established. |
| 10 | Sample size rationale | Methods—Datasets and Statistical analysis; all eligible source trials were used. No a priori power calculation; independent-participant limits discussed. |
| 11 | Missing data | Methods—Kinematic preprocessing; Supplement S2/S4; `phase5_supplement_missingness.csv`. Fold-local imputation reported. |
| 12a | Statistical analysis methods, including performance measures | Methods—Validation, diagnostics, interventions, estimands; Supplement S5–S10. |
| 12b | Predictor handling and preprocessing | Methods and Supplement S4/S7. |
| 12c | Model type, building, tuning, internal validation | Methods—Baseline models and interventions; Supplement S6/S7. |
| 12d | Assessment across subgroups or heterogeneity | Task-specific estimates; dataset/task stratification; no demographic subgroup data. |
| 12e | Model performance measures and intervals | MAE, accuracy, balanced accuracy, permutation *p*, 2,000 participant-bootstrap intervals. |
| 12f | Model updating | N/A; models were developed/evaluated within each task, not updated from an external model. |
| 12g | Calculation/use of individual predictions | Out-of-fold trial predictions generated only for evaluation; not used for decisions. |
| 13 | Class imbalance methods | Participant-average balanced accuracy; empirical permutation nulls. No resampling to rebalance classes. |
| 14 | Fairness | Discussion—Limitations and claim matrix C14. Demographic data unavailable; fairness not assessed. |
| 15 | How to obtain/use model output | N/A for deployment: no clinical model is released for use. Reproduction commands are in Supplement S14. |
| 16 | Differences between development and evaluation data | Outer folds differ by held-out participant; all preprocessing fitted to training folds. Dataset/task analyses were separate rather than cross-dataset transfer. |
| 17 | Ethics approval | Declarations. Secondary deidentified analysis; a new institutional determination is not in the record and must be confirmed before submission. |
| 18a | Funding | **Pending author completion.** |
| 18b | Conflicts of interest | **Pending author completion.** |
| 18c | Protocol availability | `docs/PROTOCOL.md`, Git tag `protocol-v1`, manuscript Methods. |
| 18d | Registration | No external registry identified. Git protocol freeze and dated deviations reported; describe as protocolized, not prospectively registered. |
| 18e | Data sharing | `data_code_availability.md`. Source access terms and restricted artifacts stated. |
| 18f | Code sharing | `data_code_availability.md`, GitHub repository, exact environment and runner. Repository license remains to be selected. |
| 19 | Patient and public involvement | Declarations: none. |
| 20a | Participant flow | Results—Feasibility; Supplement S2; source missingness tables. A journal flow diagram can be derived from Figure 1 and Table 1. |
| 20b | Participant/trial characteristics | Table 1; Supplement S2. |
| 20c | Comparison of development and evaluation samples | Fold composition supplement; held-out participants were disjoint by design. |
| 21 | Number of participants/events analyzed | Abstract, Methods, Results, Table 1: 2,501 trials; task-specific participants. Error prevalence in Supplement S2. |
| 22 | Full model specification | Analysis code/configurations are released; fold-specific fitted coefficients are not printed because models vary by fold. Sufficient code is available to regenerate them with authorized data. |
| 23a | Model performance with uncertainty | Results—Protocol gap, identity recovery, verification, utility; Tables 3–5; Figures 2–6. |
| 23b | Performance across groups/heterogeneity | Task-specific results; leave-one-participant outputs; no demographic attributes. |
| 24 | Model updating results | N/A. |
| 25 | Interpretation relative to objectives and prior work | Discussion ¶1–6. |
| 26 | Limitations | Dedicated Limitations section before Conclusion. |
| 27a | Usability and applicability | Discussion. Methodological benchmark only; no deployed interface. |
| 27b | Handling missing/out-of-range inputs in use | N/A for deployment; preprocessing rules documented for reproduction. |
| 27c | Implications and future research | Discussion and Conclusion: participant-held-out evaluation, fresh probes, prospective clinical validation. |

## TRIPOD+AI for Abstracts: 13-item mapping

| Abstract item | Location/status |
|---|---|
| Title identifies prediction-model evaluation | Title |
| Background/objectives | Purpose |
| Data source/design | Methods: retrospective four-dataset analysis |
| Setting | Methods: dry-lab task datasets |
| Participants | Methods: trial and dataset counts |
| Outcome | Methods: GRS, observed errors, image-derived error |
| Predictors | Methods: surgical kinematics |
| Sample size | Methods: 2,501 trials; task participant counts remain in main text/Table 1 |
| Missing data | Not included due abstract length; reported in Methods/Supplement |
| Statistical/model methods | Methods: paired protocols, probes, interventions, bootstrap |
| Results with uncertainty | Results: probe ranges, verified reductions, task directions and interval statement |
| Conclusions | Conclusion |
| Registration/protocol/data/code | Main Methods and Data/Code statement; external registry not used |
