"""Apply the dated correction without modifying the archived Phase 6 text."""
import re
import csv


def correct_supplement(text, root):
    text = text.replace('It accompanies the Phase 5 locked outputs.',
                        'It accompanies the original Phase 5 locked outputs and the post-lock correction of 16 November 2026 (S15).')
    text = text.replace('No model was refit for manuscript preparation.',
                        'Primary outcome and intervention models were not refit. A separate post-lock fixed-C identity diagnostic is documented in S16.')
    text = text.replace('[@Hamilton2026Paper1]', '(unpublished manuscript; project repository: https://github.com/hahnyu/surgical-skill)')
    text = text.replace('[@Sharon2025; @BGUSkillsData2025]', '[@BGUSkillsData2025]')
    text = re.sub(r'`([a-f0-9]{64})`', lambda m: r'`\nolinkurl{' + m.group(1) + r'}`{=latex}', text)
    text = text.replace(
        '`(|y_i - prediction_I3_i| - |y_i - prediction_I0_i|) / SD(y_training_for_outer_fold)`.',
        r'''```{=latex}
\[\frac{|y_i-\widehat{y}_{i,I3}|-|y_i-\widehat{y}_{i,I0}|}{\operatorname{SD}(y_{\mathrm{training,outer\ fold}})}.\]
```''')
    text = text.replace('Ridge alpha was selected from `{0.1, 1, 10, 100, 1000}`.',
        'Phase 3 baseline ridge alpha was selected from `{0.1, 1, 10, 100, 1000}`. Phase 4 linear interventions and their I0 comparator instead used fixed downstream ridge alpha=10; representation selection still used training data.')
    a = text.index('Representations were frozen before fresh probes were trained.')
    b = text.index('\n\nThe dimension-matched', a)
    text = text[:a] + '''Representations were frozen before fresh probes were trained under same-participant folds. Held-out-participant representations were fitted separately, so these checks do not verify each held-out transformation. The corrected I4-minus-capacity linear balanced-accuracy difference is -0.048 (95% interval -0.098 to +0.002), and the nonlinear difference is -0.003 (-0.045 to +0.043). Neither verifies reduction. I3-minus-I0 differences are -0.184 (-0.214 to -0.153) for the linear probe and -0.138 (-0.175 to -0.100) for the nonlinear probe. The original I4-to-I3 decision remains unchanged; these corrected intervals were computed after the original results were known. I3 aggregates ten dataset-task groups and I4 seven outcome-eligible groups; the two interventions were not compared head to head on a common aggregate cohort.''' + text[b:]
    text = text.replace('For identity verification, groups were averaged equally and I4 additionally averaged its three seeds. Leave-one-participant summaries were calculated for every primary estimand.',
        'For corrected aggregate identity verification, seeds were first averaged within participant and task. Participants were then resampled within dataset, with each sampled participant carrying all available tasks, preserving cross-task dependence. Task groups were averaged equally. The seed was 20261116 and percentile endpoints used linear interpolation at 0.025 and 0.975. Any draw with no sampled participant for a task would be rejected in its entirety; no such draws occurred. Intervals condition on the saved predictions and do not include model-refitting uncertainty. Leave-one-participant summaries omit scored participant effects without refitting models.')
    text = text.replace('Empirical permutation *p* values used `(1 + count(null >= observed)) / (1 + number of permutations)` with the appropriate directional statistic. No correction across tasks was used because the analysis reports task-specific estimands and treats the permutation results as replicated diagnostics.',
        'The archived identity null used fixed-C=1 logistic regression, whereas observed logistic and forest probes selected hyperparameters. The formerly reported identity p values are withdrawn because the pipelines were not matched. No formal permutation-test claim is made for those descriptive accuracies. The participant-wise versus record-wise JIGSAWS comparison reports the distribution of paired accuracy differences under two distinct shuffling schemes. Its plus-one nonpositive tail fraction is not a valid hypothesis-test p value for a common exchangeable null and is no longer labeled as one.')
    text = text.replace('# S10. Full locked numerical results', '# S10. Numerical results with corrected interpretation')
    a = text.index('| Dataset/task | Linear BA'); b = text.index('## S10.2', a)
    section = text[a:b]
    section = section.replace(' | Record-wise null median', '')
    section = section.replace('|---|---:|---:|---:|', '|---|---:|---:|')
    section = re.sub(r'(\| [^\n]+ \| 0\.\d+ \| 0\.\d+) \| 0\.\d+ \|', r'\1 |', section)
    section = section.replace('Each full-feature probe exceeded its 50-permutation record-wise null at empirical *p*=0.0196.',
                              'Observed balanced accuracies are descriptive. No matched permutation p value is available for either tuned model.')
    text = text[:a] + section + text[b:]
    text = text.replace('| Empirical *p* |', '| Nonpositive paired differences |')
    text = text.replace('| 0.004975 |', '| 0 / 200 |')
    text = text.replace('No deviation changed the participants, primary targets, validation unit, primary estimand, participant-level inference, or prespecified I4-to-I3 fallback rule after task effects were inspected.',
        'The original deviations did not change participants, primary targets, or the I4-to-I3 fallback rule. The post-lock correction in S15 changes aggregate identity uncertainty and inferential reporting after results were known; it is not presented as a prespecified analysis.')
    text += '''

# S15. Post-lock technical correction, 16 November 2026

The original Phase 3--5 files and their manifest hashes are preserved as historical artifacts. The current submission supersedes their aggregate identity intervals and unmatched permutation-test claims. Corrected sources are in `results/corrections/2026-11-16/`; the analysis manifest records input and output hashes, and the package manifest records submission sources and PDFs.

The correction (1) keeps each dataset-participant's tasks together during aggregate identity resampling after seed averaging; (2) withdraws unmatched identity-test p values and relabels the two-scheme JIGSAWS shuffle comparison descriptively; (3) replaces the pooled cross-task utility plot with identity effects and explicitly matched controls; (4) uses participant-average skill accuracy and the Table 5 GRS intervals in Figure 6; and (5) clarifies fixed versus tuned ridge penalties, the same-participant scope of fresh probes, and the lack of refitting in uncertainty and influence calculations. I3 remains the primary intervention, and no consistent held-out utility benefit emerges.

The corrected bootstrap and figure data use saved aggregate participant effects and metrics. Private feature and prediction files were initially cloud-evicted, but became locally available during the correction. The primary outcome and intervention predictions were unchanged. A separate matched fixed-C identity diagnostic was then verified as described in S16; it does not validate the withdrawn p values for the tuned probes.

Reproduce the correction and submission after installing the documented dependencies:

```bash
python scripts/build_technical_corrections.py
python submission/ijcars/build_submission.py
python scripts/validate_ijcars_submission.py
```

The historical Phase 5 runner reproduces the archived analysis, not this correction. The draft validator checks numerical consistency and PDF rendering diagnostics. The separate `--final` gate also requires completed human disclosures, ethics/source-permission confirmation, author approval, originality confirmation, and public availability of the corrected analysis release. Outstanding items are recorded in the submission checklist.
'''
    text += '''

# S16. Matched fixed-C identity diagnostic (post-lock exploratory analysis)

To address the mismatched original identity null, we fitted an observed multinomial logistic probe with C=1, matching the original 50 record-wise label-permutation models. Features, trial/fold assignments, median imputation, standardization, solver, and penalty were identical; no hyperparameter selection was performed in either pipeline. Feature and null-prediction hashes were verified against the frozen inputs, and every permutation preserved the observed trial/fold set and label counts. This diagnostic was added after inspecting results, rather than prespecified as the observed test.

Balanced accuracy gives equal weight to identity classes. The unadjusted Monte Carlo p value is `(1 + count(null >= observed)) / 51`. All ten observed statistics exceeded all 50 matched null statistics, giving p=1/51 (approximately 0.01961) in each task. This is the smallest attainable p value with 50 draws, not evidence for a smaller tail probability. This is a conditional random-label diagnostic for these fixed records, not population-level inference about unseen operators. These exploratory, task-specific p values are not adjusted for multiple testing and do not establish an omnibus or family-wise significance claim. They apply only to this fixed-C logistic diagnostic, not to the tuned logistic or random-forest probes in Table 4.

| Dataset/task | Fixed-C balanced accuracy | Matched null median |
|---|---:|---:|
'''
    with (root / 'results/corrections/2026-11-16/identity_matched_null.csv').open(newline='') as handle:
        for row in csv.DictReader(handle):
            text += f"| {row['dataset']} / {row['task']} | {float(row['balanced_accuracy']):.3f} | {float(row['null_median']):.3f} |\n"
    text += '''
The observed diagnostic was regenerated and its aggregate outputs agreed within 1e-12 with the first run. Code is `scripts/run_matched_identity_diagnostic.py`; aggregate results and the input/output hash manifest are in the dated correction directory. Individual predictions remain private. Reproduction requires restoring the authorized private feature and null-prediction inputs and running this diagnostic before rebuilding the correction and submission package.
'''
    return text
