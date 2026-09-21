# Surgical skill identity-suppression study

This repository implements the prospective protocol in
[`SECOND_PAPER_CODEX_MASTER_PLAN.md`](../SECOND_PAPER_CODEX_MASTER_PLAN.md).
The scientific question is whether suppressing operator-identifying information
changes same-operator performance and generalization to an unseen operator.

The repository is currently stopped at the Phase 1 human-review gate. No
predictive models have been trained here.

## Local JIGSAWS connection

The restricted JIGSAWS release remains in the paper-1 project. This project uses
a Git-ignored symbolic link:

```text
data/raw/jigsaws -> /Users/hahnyu/Documents/surgical-skill/data
```

To reproduce this on another machine, create `data/raw/jigsaws` as a link to an
authorized local JIGSAWS copy. Never commit the linked files. See
[`data/README.md`](data/README.md) and the Phase 1 manifest for provenance.

## Current gate

Review [`reports/feasibility_report.md`](reports/feasibility_report.md) before
authorizing Phase 2. The protocol is frozen at the annotated Git tag
`protocol-v1`.

