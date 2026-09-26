# Surgical skill identity-suppression study

This repository implements the prospective protocol in
[`SECOND_PAPER_CODEX_MASTER_PLAN.md`](SECOND_PAPER_CODEX_MASTER_PLAN.md).
The scientific question is whether suppressing operator-identifying information
changes same-operator performance and generalization to an unseen operator.

Phases 0–6 are complete. Phase 4 fitted the prespecified identity interventions
and designated I3 linear identity-subspace removal as the primary comparison
after I4 failed nonlinear-probe verification. Phase 5 locks the exact inputs,
participant-level inference, robustness outputs, six figures, and five main
tables. Phase 6 converts the locked analysis into a manuscript, detailed
supplement, data/code statement, adapted TRIPOD+AI checklist, claim-evidence
matrix, and submission checklist under [`paper/`](paper/).

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

## Phase 5 locked analysis

The final locked results are documented in
[`reports/final_results.md`](reports/final_results.md). Run the complete gate,
including a byte-identical second build, with:

```bash
.venv/bin/python scripts/run_phase5_locked.py
```

Machine-readable participant estimates, bootstrap and permutation outputs,
figure sources, tables, and the complete artifact manifest are under
`results/` and `data/manifests/phase5_artifacts.csv`.

## Phase 6 manuscript package

The conservative manuscript is [`paper/manuscript.md`](paper/manuscript.md),
with methods and robustness detail in [`paper/supplement.md`](paper/supplement.md).
Validate manuscript structure, citations, locked numerical claims, construct
language, and reporting matrices with:

```bash
.venv/bin/python scripts/validate_phase6.py
```

Author-supplied submission metadata still required by a journal is isolated in
[`paper/submission_checklist.md`](paper/submission_checklist.md); it does not
alter the locked scientific analysis.
