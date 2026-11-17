# Corrected IJCARS submission draft

The current package incorporates the **16 November 2026 post-lock correction**. It is a reviewable draft, not cleared for submission. Original Phase 3–5 artifacts remain unchanged; their unmatched identity p values and original aggregate identity intervals are superseded. See `../../reports/technical_corrections_2026-11-16.md`.

## Build and validate

Use Python 3.12 with the project's pinned analysis dependencies, the `submission` optional dependencies in `pyproject.toml`, and pytest. System tools: Pandoc, latexmk, pdflatex, BibTeX, and Poppler (`pdftotext`, `pdfinfo`, `pdftoppm`).

```bash
python scripts/build_technical_corrections.py
python submission/ijcars/build_submission.py
python scripts/validate_ijcars_submission.py
python scripts/validate_ijcars_submission.py --final
```

Run from the repository root. The last command intentionally fails until human confirmations are complete. It does not send or upload anything. The correction bootstrap uses available participant-effect CSVs and aggregate metrics and does not refit primary models. The separately reported fixed-C identity diagnostic is regenerated with `python scripts/run_matched_identity_diagnostic.py`; it requires the authorized private inputs and verifies their original hashes. Its aggregate result can be used to rebuild the submission without redistributing private data.

The November verification used `/tmp/surgical-skill-corrections-venv/bin/python`, with the same pinned scientific versions, because the original `.venv` files had been cloud-evicted. Private feature and null-prediction inputs later became available, allowing the supplementary matched diagnostic to be verified. `PYTHONPYCACHEPREFIX=/tmp/surgical-pycache` and pytest `-p no:cacheprovider` avoided evicted caches. This temporary environment is disposable; it is not a new scientific environment specification.

The corrected package is published on the public `codex/ijcars-submission` branch. Author contributions, final manuscript approval, authorized data access, applicable permissions, and the absence of identifiable participants or linkage-key access have been confirmed. No formal Cornell ethics determination was obtained; the manuscript states this explicitly. The human-authored AI disclosure and originality/no-concurrent-submission confirmation remain outstanding.

## Sources that persist on rebuild

- `build_submission.py`: main text, abstract, tables, and build logic.
- `corrected_supplement.py`: dated amendments to the archived supplementary text.
- `corrected_figures.py`: corrected figures and machine-readable plot sources.
- `ai_use_disclosure.md`: human-authored disclosure inserted in Methods.
- `declarations.md`: ethics, contributions, funding, conflicts, availability.
- `cover_letter.tex`: editable cover letter; update its date when actually submitting.
- `author_confirmations.json`: explicit completion flags, initially false.

Do not edit only generated `manuscript.tex` or `supplement.tex`: rebuilding replaces them. `paper/` and the original phase runners describe the historical analysis, not the corrected submission.

## Deliverables and provenance

The build produces `output/pdf/ijcars_manuscript.pdf`, `output/pdf/ESM_1.pdf`, and `output/pdf/ijcars_cover_letter.pdf`; editable LaTeX, numbered bibliography, and six vector figures live here. `build_metadata.json` contains the computed inclusive word count; `portal_abstract.txt` supplies the current abstract for portal entry. `package_manifest.json` hashes source and output artifacts. Corrected inference, bootstrap draws, figure source data, and their analysis manifest are in `results/corrections/2026-11-16/`.

After completing the checklist, upload the editable main source, `references.bib`, and `figures/`; use the main PDF for review, `ESM_1.pdf` as Online Resource 1, and the cover-letter PDF for the letter. Keep confirmation files, internal review notes, and private participant-level data out of the journal upload.
