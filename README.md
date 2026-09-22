# Surgical skill identity-suppression study

This repository implements the prospective protocol in
[`SECOND_PAPER_CODEX_MASTER_PLAN.md`](SECOND_PAPER_CODEX_MASTER_PLAN.md).
The scientific question is whether suppressing operator-identifying information
changes same-operator performance and generalization to an unseen operator.

Phases 0–2 are complete. The repository is stopped before Phase 3 model
development. No predictive models have been trained here.

## Local JIGSAWS connection

The restricted JIGSAWS release remains in the paper-1 project. This project uses
a Git-ignored symbolic link:

```text
data/raw/jigsaws -> /Users/hahnyu/Documents/surgical-skill/data
```

To reproduce this on another machine, create `data/raw/jigsaws` as a link to an
authorized local JIGSAWS copy. Never commit the linked files. See
[`data/README.md`](data/README.md) and the Phase 1 manifest for provenance.

## Phase 2 preprocessing

The deterministic loaders normalize 2,501 trials into one schema, compute a
fixed feature set, and generate both same-participant and held-out-participant
fold manifests. Raw inputs and the harmonized feature matrix remain ignored;
the pseudonymous folds and descriptive tables are committed.

Run the gate after acquiring the authorized data:

```bash
uv sync --all-groups
.venv/bin/python scripts/build_phase2_dataset.py --write-public
.venv/bin/python scripts/build_phase2_dataset.py \
  --private-output data/processed/private/phase2_features_rerun.csv
.venv/bin/pytest -q
.venv/bin/python scripts/validate_phase2.py
```

See [`reports/phase2_descriptive_report.md`](reports/phase2_descriptive_report.md)
for the reconciled cohort and preprocessing decisions. The prospective
protocol remains frozen at the annotated Git tag `protocol-v1`.
