# Decision 0001: reuse paper-1 data without modifying paper 1

**Date:** 2026-09-21  
**Status:** accepted for Phase 1

The existing paper-1 repository is treated as a read-only source. At audit time:

- path: `/Users/hahnyu/Documents/surgical-skill`
- Git commit: `fd6db3d35539aff571b76e379b032a9f92f7eb4a`
- remote: `https://github.com/hahnyu/surgical-skill.git`
- `src/loaders.py` SHA-256:
  `60cf096e1508d0b5888e289542a31d25106d9d46198d07f2139358d8e6669c74`
- `src/features.py` SHA-256:
  `3771ee69246fb1a2437115be703a2ab77b342ea24a711d6c6ddf546c5655e42b`

This repository connects to its authorized data directory through the ignored
`data/raw/jigsaws` symlink. Phase 2 may port loader or feature code only with
tests and attribution to the source commit; no source-tree mutation is allowed.

