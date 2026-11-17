# Technical correction record — 16 November 2026

The corrected IJCARS draft supersedes the inferential and reporting statements identified below. Original Phase 3–5 outputs and `paper/` are preserved for provenance. This is an explicitly post-lock correction made with knowledge of the results, not a new prespecified analysis.

## Scientific corrections

| Issue | Correction and consequence |
|---|---|
| Aggregate identity bootstrap treated each task/seed array independently | Average seeds within participant/task, resample each dataset-participant jointly across all their available tasks, and preserve equal task weights. Use 2,000 draws, seed 20261116, and interpolated percentile endpoints. This conditions on saved predictions; models are not refitted. |
| Unmatched identity permutation null | Remove tuned-logistic and forest p values from the active manuscript/supplement. The original null fitted fixed-C=1 logistic models, so neither tuned observed pipeline is matched. Retain observed balanced accuracy as descriptive evidence. A separate post-lock fixed-C logistic diagnostic was fitted against the correctly matched null, reproduced, and reported only as an exploratory Supplement S16 result. Its ten unadjusted p values are each 1/51; this is the 50-draw resolution floor, not a family-wise or omnibus claim. |
| JIGSAWS two-scheme shuffle comparison | Replace the misleading p-value label with the median paired difference and count of nonpositive paired differences: zero of 200 in each task. Comparing two distinct shuffling distributions is descriptive, not a randomization test under a common exchangeable null. |
| Pooled utility/identity scatter | Replace Figure 4 with corrected identity-effect intervals, showing the proper I0 or capacity-control comparator and group count. Do not average heterogeneous task utility. |
| Fresh-probe scope and ridge selection | Explain that fresh identity probes verify separately fitted same-participant representations, not each held-out representation. Phase 3 ridge penalties were tuned; Phase 4 linear intervention/comparator ridge alpha was fixed at 10. |
| Figure 6 weighting and interval mismatch | Use participant-average skill accuracy for each JIGSAWS task and the same seed-averaged held-out GRS effects and intervals as Table 5. Remove the ad hoc repair of missing SVG bars using trial-average accuracy. |
| Plot readability | Replace the schematic and primary forests with readable vector diagrams. Figures 2 and 5 use explicitly labeled task-specific axes so the ROSMA extreme does not compress other effects. Figure 5 shows the primary I3 comparison; all controls remain in machine-readable tables. |
| Influence claims | Specify that leave-one-participant summaries omit scored participant effects without refitting. Bootstrap intervals do not measure model-refitting uncertainty. |

Corrected aggregate probe effects (candidate minus comparator):

| Candidate / comparator | Probe | Estimate | 95% interval | Tasks |
|---|---|---:|---|---:|
| I3 / I0 | Linear | -0.184 | [-0.214, -0.153] | 10 |
| I3 / I0 | Nonlinear | -0.138 | [-0.175, -0.100] | 10 |
| I4 / capacity | Linear | -0.048 | [-0.098, +0.002] | 7 |
| I4 / capacity | Nonlinear | -0.003 | [-0.045, +0.043] | 7 |

I3 still meets the two-probe verification rule. Neither I4 interval now verifies suppression, so the original I4-to-I3 fallback remains unchanged. The interventions use different aggregate task cohorts and are not a head-to-head comparison. Primary held-out utility remains task-specific: one of seven point estimates favors I3, six favor I0, and six intervals cross zero. This is not evidence of equivalence or proof that suppressing all identity cannot help.

## Submission and reproducibility corrections

- Remove unsupported assertions of IRB status, author contributions/final approval, originality, and absence of concurrent submission. The corresponding human confirmations remain pending. No institutional determination is invented.
- Accurately identify the code repository as private and require a reviewer-access arrangement or permitted release before submission.
- Keep funding and conflicts exactly as supplied by the user.
- Put the human-written AI disclosure in Methods via persistent `ai_use_disclosure.md`; it survives rebuilds.
- Correct supplementary raw-LaTeX rendering and duplicate heading numbers; display dataset DOI URLs; describe the unpublished overlapping manuscript in prose instead of a malformed bibliographic author entry. Cite the published BGU-SKILLS dataset record without relying on the preprint reference.
- Compute the inclusive word count from the final rendered PDF, export the current portal abstract, and hash source/output artifacts. Build dependencies are recorded in `pyproject.toml`.
- Replace stale submission metadata, checklist, and ethics-request guidance. Draft validation permits explicit pending statements; `--final` rejects outstanding confirmations and placeholders.

## Artifacts and preservation boundary

`results/corrections/2026-11-16/` contains corrected effect estimates, all 24,000 bootstrap draws (12 comparisons/probes × 2,000), descriptive identity and skill diagnostics, plot sources, and the analysis manifest. `submission/ijcars/package_manifest.json` hashes the active package. The original Phase 5 manifest remains unchanged:

`a4345fc8cdcb50b90e286914ff6dec8ec1c7373e248f60a260c4eaf11f0d9bc3`

Original environment files and private features/predictions were initially cloud-evicted. Scientific package versions were restored in a temporary environment. The private feature and null-prediction files subsequently became readable; both hashes were verified, and the fixed-C observed diagnostic was regenerated. The second diagnostic run agreed with the first within 1e-12. All primary outcome and intervention predictions remain unchanged; only this supplementary identity diagnostic adds model fits. The original unsupported inference for tuned probes remains withdrawn.

The earlier review-only JSON used order-statistic endpoints. The correction uses interpolated percentile endpoints and is authoritative for this draft; the minor endpoint differences are Monte Carlo/quantile-convention differences, not changed point estimates.

## Validation

- Matched identity diagnostic: all ten task outputs reproduced within 1e-12; source feature/null hashes, every permutation trial/fold set, and identity label counts verified.
- Full repository regression suite: **24 passed** (including tests that repeated correlated tasks/seeds do not spuriously narrow uncertainty and that a mismatched permutation specification is rejected).
- Corrected draft validator passes: source/figure consistency, corrected numerical statements, abstract/word limits, numbered references, displayed DOI URLs, required artifacts, analysis hashes, and clean final LaTeX logs.
- Final-submission gate intentionally fails on five pending human-confirmation categories. This is expected and prevents treating a prepared draft as approved for upload.
- Rendered manuscript, supplement, and cover letter are inspected for layout. The current word count is generated in `submission/ijcars/build_metadata.json`, rather than copied into this record.

## Reproduce

```bash
python scripts/build_technical_corrections.py
python submission/ijcars/build_submission.py
python scripts/validate_ijcars_submission.py
python -m pytest -p no:cacheprovider
```

Use the pinned project dependencies plus the `submission` optional dependencies, Pandoc, TeX/BibTeX/latexmk, and Poppler. See `submission/ijcars/README.md` for environment and human-completion instructions. Running the archived phase runners alone does not apply this amendment.


## Author confirmations (16 November) and public release (17 November 2026)

After the initial review, the corresponding author supplied all authors' contribution roles and final manuscript approval, confirmed authorized data access and applicable permissions, and explicitly confirmed that no investigator could identify participants or access a re-identification key. The author also confirmed that no formal Cornell determination had been obtained. The current ethics statement reports those facts without claiming institutional approval or exemption. Public repository visibility was verified, and the corrected package is published on `codex/ijcars-submission`. The earlier pending-status descriptions above preserve the initial review state; the active checklist and confirmation file reflect the updated status. AI disclosure and originality/no-concurrent-submission confirmation remain pending.
