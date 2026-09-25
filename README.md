# Surgical skill identity-suppression study

This repository implements the prospective protocol in
[`SECOND_PAPER_CODEX_MASTER_PLAN.md`](SECOND_PAPER_CODEX_MASTER_PLAN.md).
The scientific question is whether suppressing operator-identifying information
changes same-operator performance and generalization to an unseen operator.

Phases 0–4 are complete. The repository is stopped before Phase 5 manuscript
synthesis and robustness work. Phase 4 fitted the prespecified identity
interventions and designated I3 linear identity-subspace removal as the primary
comparison after I4 failed nonlinear-probe verification.

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

## Phase 3 audit

The baseline replication, identity probes, formal JIGSAWS permutations,
negative controls, and leakage canary are documented in
[`reports/audit_report.md`](reports/audit_report.md). Aggregate metrics and
private prediction hashes are committed; trial-level predictions remain local
under `results/predictions/private/`.

## Phase 4 interventions

The identity-suppression results, primary-comparison decision, held-out-user
effects, JIGSAWS skill endpoint, controls, and seed stability are documented in
[`reports/intervention_report.md`](reports/intervention_report.md). Aggregate
tables are under `results/metrics/`, and
[`data/manifests/phase4_artifacts.csv`](data/manifests/phase4_artifacts.csv)
records the hashes of all private out-of-fold artifacts.
