# Phase 3 results

`metrics/` contains aggregate tables regenerated from saved out-of-fold
predictions by `scripts/summarize_phase3.py`. Each row records the immutable
analysis commit and configuration hash.

Trial-level prediction artifacts are stored locally under
`predictions/private/` and are ignored by Git because the combined analysis
includes the access-controlled JIGSAWS release. Their filenames, row counts,
and SHA-256 hashes are committed in
`data/manifests/phase3_artifacts.csv` so an authorized checkout can verify an
exact regeneration.
