# Locked analysis results

`metrics/` contains aggregate tables regenerated from saved out-of-fold
predictions by `scripts/summarize_phase3.py`. Each row records the immutable
analysis commit and configuration hash.

Trial-level prediction artifacts are stored locally under
`predictions/private/` and are ignored by Git because the combined analysis
includes the access-controlled JIGSAWS release. Their filenames, row counts,
and SHA-256 hashes are committed in
`data/manifests/phase3_artifacts.csv` so an authorized checkout can verify an
exact regeneration.

Phase 4 intervention aggregates are also stored in `metrics/`. Phase 5 adds:

- `locked/`: participant-level effects, all bootstrap draws, permutation
  outputs, leave-one-participant sensitivity, and verified input hashes;
- `figures/`: six deterministic SVG figures plus CSV source data;
- `tables/`: five main analysis tables and supplement source tables.

`scripts/run_phase5_locked.py` regenerates the aggregates, locked analysis,
figures, tables, and manifest twice and verifies byte-identical output hashes.
