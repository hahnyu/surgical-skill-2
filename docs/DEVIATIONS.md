# Protocol deviations

Protocol frozen: 2026-09-21. No deviations recorded at freeze.

| Date | Change | Reason | Outcomes inspected? | Likely bias | Mitigation |
|---|---|---|---|---|---|
| 2026-09-21 | Phase 0 repository transcription and the Phase 1 source audit occurred in one authorized work session; the source master specification itself was already fixed. | The paper-2 repository was empty when Phases 0–1 began. Dataset documentation, counts, and target formulas were checked while transcribing the protocol, before creating the `protocol-v1` Git object. | Dataset metadata and raw target distributions were inspected; no model predictions, fitted effects, or intervention results existed or were inspected. | Could favor external targets that look feasible, but cannot select among model results. | Eligibility follows the source specification's predeclared provenance/circularity rules; all candidates, anomalies, and rejection reasons are retained in the Phase 1 tables. |

