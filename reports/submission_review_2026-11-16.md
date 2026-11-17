# Submission review — 16 November 2026

## Decision

Do not submit the October package unchanged. The core contribution remains plausible and useful: identity is decodable from kinematics; I3 reduces tested identity recovery; this does not consistently improve unseen-participant prediction. However, statistical calibration, interpretation, ethics assertions, and submission artifacts need correction. The earlier statement that the package was complete was too strong.

This review inspected the manuscript/build source, supplementary PDF, cover letter, phase reports/configurations, identity intervention and aggregation code, saved participant effects, and current Cornell/IJCARS guidance. It is not a full independent raw-data replication or an exhaustive verification of every citation. Existing submission and Phase 6 validators pass; they check predetermined claims and formatting and do not establish statistical correctness. A bounded pytest attempt exceeded 45 seconds and was stopped; no new suite pass is claimed.

## Required corrections, in priority order

1. **Identity permutation p-values are not matched to the tested pipeline.** In `scripts/run_phase3_audit.py:351`, null predictions use only fixed-C multinomial logistic regression. `scripts/summarize_phase3.py:113` compares that shared null against multiple observed models, including tuned logistic regression and random forests. Generate nulls using each observed pipeline, including its selection procedure, or restrict inference to an identically specified observed fixed-C logistic model. Revisit the abstract, main results, Table 4, and supplement. Fifty permutations give a minimum attainable p of 1/51; do not present the repeated floor value as precise strong evidence. Larger matched permutation runs would improve resolution. The descriptive accuracy estimates are separate from this calibration issue.

2. **Aggregate probe intervals break dependence across tasks/seeds.** `scripts/summarize_phase4.py:148` independently resamples arrays grouped by dataset/task/seed. Participants recur across tasks, and model seeds are not independent participant cohorts. Average seeds within participant/task and resample participants jointly across tasks within dataset, preserving equal task weights. A review-only calculation from saved participant effects gives approximately:

   | Comparison | Probe | Difference | Review 95% interval |
   |---|---|---:|---:|
   | I3 minus I0 | Linear | -0.1841 | [-0.2145, -0.1533] |
   | I3 minus I0 | Nonlinear | -0.1379 | [-0.1748, -0.0999] |
   | I4 minus capacity control | Linear | -0.0478 | [-0.0983, +0.0017] |
   | I4 minus capacity control | Nonlinear | -0.0031 | [-0.0455, +0.0430] |

   Reproduce with `python3 reports/review_cluster_bootstrap.py`. This is a sensitivity calculation, not a replacement locked analysis. I3 still passes both probe criteria; I4 still fails, but the statement that I4 clearly reduces the linear probe is no longer supported by this interval. Document any correction as a dated post-lock amendment. Fixed-prediction bootstraps also omit refitting/training variability; state that limitation. Leave-one-participant summaries likewise omit a participant's scored errors, rather than refitting every model without that person.

3. **Figure 4 contradicts the stated analysis and its own caption.** `scripts/build_phase5_analysis.py:781` pools standardized absolute error across heterogeneous tasks, although the manuscript says tasks are not pooled. The axes are absolute accuracy/error, while the caption describes changes. Identity includes ten task groups; utility includes seven. I4 is displayed without its own capacity-control reference. Replace with task-specific paired changes using the correct comparator, or remove it from the main paper. The extreme ROSMA outcome makes the pooled display especially misleading.

4. **The ethics conclusion and author approvals are not established by the files.** The manuscript/cover letter claim that Cornell review was unnecessary; the cover letter also asserts all authors approved and no simultaneous submission exists. The earlier request supplied names, no funding, and no conflicts, but not evidence for all these additional statements. Confirm actual contributions, affiliations, approval, submission status, identifier/key access, and source-provider involvement. Do not represent a policy interpretation as an institutional determination.

5. **Separate identity verification from unseen-participant suppression.** `scripts/run_phase4_linear.py` trains fresh identity probes only for same-participant folds; utility uses separately fitted held-out-participant transformations, potentially with different selected ranks. That is a legitimate diagnostic design, but the text should not imply that each representation used for unseen-participant utility was itself independently verified. Explain this distinction. Also distinguish the tuned Phase 3 ridge baseline from the fixed-alpha=10 Phase 4 intervention comparisons; both are currently described too generically.

6. **Figure 6 has divergent source and submission data.** The locked figure CSV has NA for both skill bars because the generator filters `multinomial_logistic` while the actual model is `skill_logistic`. The submission builder patches only the SVG bars from a different table. Repair the source generation through a documented amendment and rebuild all dependent artifacts. Use the declared participant-average endpoint consistently rather than trial-weighted `accuracy`, and reconcile displayed confidence intervals across Table 5/Figures 5–6, which currently use different bootstrap outputs/seeds.

7. **The code availability claim is not currently actionable.** `gh repo view` confirmed `hahnyu/surgical-skill-2` is PRIVATE, with default branch `codex/phases-0-1`; the package is on `codex/ijcars-submission`. Choose public release after a data-license/privacy audit, a clean public code-only archive, or an accurately described controlled reviewer-access route. Do not make the whole repository public without checking existing participant-level tables, manifests, and history. Verify the JIGSAWS agreement covers this project/team and identity-probe use; do not assume either permission or a prohibition without reading the agreement.

8. **Actual PDF defects and bibliography gaps remain.** Supplement page 4 visibly prints `{=latex}` and a literal `\\nolinkurl{...}` command. Supplement headings are double-numbered (e.g. `4 S4.`). Some dataset/preprint DOIs present in the BibTeX source are omitted by the rendered bibliography; check every entry against its source, including current publication status. The supplement cites the earlier unpublished paper as author `Hamilton`, while the main paper discloses it in text. IJCARS asks that unpublished works be mentioned in text. Figures need larger readable labels, explicit units/scales, and self-contained captions; Figure 6 bars lack numeric scale labels.

9. **Submission tooling can overwrite human edits and certify stale assertions.** `build_submission.py` regenerates manuscript.tex and hardcodes declarations/AI placeholder; editing only manuscript.tex loses the disclosure on rebuild. The validator requires the placeholder and the unconfirmed ethics wording and hardcodes the exact word count. Use one editable declarations/disclosure source and separate draft validation from final submission validation. Final checks should reject placeholders, validate the actual word range, and check the rebuilt PDFs. Record `svglib`/`reportlab` and LaTeX/Pandoc requirements; they are absent from the project dependency specification. Update the cover-letter date at actual submission.

## Improvements after the corrections

- Keep the conclusion narrow: reduced tested identity decodability does not imply identity-free features or prove that identity causes the generalization gap.
- Add a transparently labeled sensitivity for the retained ROSMA coordinate-spike trial and sparse outcome. Preserve the original locked result; do not silently remove an unfavorable record.
- Describe how weakly identified person-constant experience categories differ from expert-rated GRS. Retain the existing nonclinical caveats and Paper 1 overlap disclosure.
- Strengthen the discussion of identity versus genuine stable skill and the limitations of selecting I4 using training-head accuracy. A stronger adversarial baseline would be an exploratory addition, not a new prespecified result.
- Prioritize corrected uncertainty/null tests and clearer figures over adding architectures or datasets solely to pursue positive findings.

## What Hamilton needs to do

1. Ask Cornell IRB for a written determination using the companion reviewed email. Include the actual data-access facts and existing-analysis timeline, and involve the faculty advisor. Do not claim retrospective approval.
2. Locate the JIGSAWS access agreement and confirm permitted users/uses; tell the advisor whether any team member can identify participants, access a linking key, or identify people from available video/metadata.
3. Obtain each author's confirmation of name, current appropriate affiliation, contribution, funding/conflicts, and final manuscript approval. Confirm the current status of the earlier JIGSAWS paper and any overlapping submissions.
4. Write the substantive AI-use disclosure yourself, as requested earlier. Describe actual assistance and human checks; do not attest to checks that have not happened. IJCARS places substantive LLM disclosure in Methods, so move the completed statement there.
5. Resolve the technical corrections above and rebuild all artifacts before signing off. These are analysis/editorial tasks, not something the user needs to fix manually.
6. Decide how reviewers/readers will access the code. A public release requires a separate privacy/license check of the proposed public files/history.
7. Confirm the live submission portal with `ijcars.edoffice@cars-int.org`: the official Editorial Manager link still displays an under-development warning in the fetched page. Do not assume that warning proves submission is impossible; obtain the live route from the office.
8. Submit as Original Article after corrections and approvals. Upload editable LaTeX/BibTeX/figure sources, supplement as Online Resource 1, cover letter, and portal metadata. If avoiding an APC, select subscription publication rather than paid open access unless institutional coverage is confirmed. No APC applies to the subscription route per the publisher.

## Ethics interpretation and sources checked 16 November 2026

The likely route, conditional on the actual access facts, is a not-human-participant-research determination for secondary coded/de-identified records, rather than full IRB approval. Predicting dataset codes is not automatically identifying named people. Nevertheless, all team members' ability to ascertain actual identities and the access agreement matter. Public availability or lack of funding alone does not settle this.

Cornell's current FAQ says existing nonidentifiable data may not require review; an exemption determination, when applicable, must be made by IRB staff. The linked secondary-data guidance is dated September 2014 and explicitly warns it has not been updated for January 2019 regulatory changes; it also includes data-provider participation and access-agreement conditions. Therefore use the current IRB office to settle this project's classification. Our recommendation for written confirmation follows the unresolved facts; it is not a claim that every public-data study must apply.

- https://researchservices.cornell.edu/resources/irb-faqs
- https://researchservices.cornell.edu/offices/IRB
- https://researchservices.cornell.edu/policies/irb-guidance-research-involving-existing-or-secondary-data-documents-or-records
- https://link.springer.com/journal/11548/submission-guidelines
- https://link.springer.com/journal/11548/how-to-publish-with-us
- https://link.springer.com/journal/11548/contact-the-journal
- https://www.editorialmanager.com/cars/
