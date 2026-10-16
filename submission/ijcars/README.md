# IJCARS submission package

This directory contains the LaTeX source and submission support files for the Original Article:

> Operator identity and out-of-user generalization in automated surgical skill assessment: a multi-dataset evaluation

## Build

From the repository root:

```bash
.venv/bin/python submission/ijcars/build_submission.py
```

The build converts the six locked SVG figures to vector PDF, regenerates numbered-reference LaTeX from the locked Markdown manuscript and supplement, compiles all three documents, and writes:

- `output/pdf/ijcars_manuscript.pdf`
- `output/pdf/ESM_1.pdf`
- `output/pdf/ijcars_cover_letter.pdf`

## Submission files

- `manuscript.tex`: main LaTeX source with numbered citations, five tables, six figures, author details, ethics, funding, conflicts, contributions, and availability statements.
- `supplement.tex`: detailed supplementary methods, locked results, deviations, and reproducibility information.
- `cover_letter.tex`: journal-specific cover letter.
- `references.bib`: submission bibliography.
- `figures/Fig1.pdf` through `Fig6.pdf`: journal-numbered vector figures generated from the locked SVG files.
- `ai_use_disclosure_PLACEHOLDER.md`: instructions for the human-authored disclosure.
- `ethics_determination_request.md`: ready-to-send Cornell IRB confirmation request if the editor asks for a determination letter.

## Required human action

Replace the yellow AI-use placeholder in the manuscript with the authors’ own disclosure before submission. Confirm that the contribution statement accurately reflects each author’s role. No other scientific or numerical placeholders remain.

## Validate

```bash
.venv/bin/python scripts/validate_ijcars_submission.py
```

Upload `manuscript.tex`, `references.bib`, and `figures/` as the editable main source; upload `ESM_1.pdf` as Online Resource 1 and `ijcars_cover_letter.pdf` as the cover letter. The compiled manuscript PDF is included for review and visual verification.
