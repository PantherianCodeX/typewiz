# Draft-2 preservation map (backbone extraction)

List the *architectural* items from the draft-2 ADR set that must be preserved (or explicitly superseded by the plan). This is not a restatement of the sources—this is the extraction list and its destinations.

| Item ID | Draft-2 source (ID + anchor) | Backbone type (taxonomy/naming/boundary/object class/invariant) | Preserve posture (`verbatim`/`adapt`) | Destination owner (doc) | Destination anchor | Superseded by plan? (Y/N + ref) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P-0001 | D2-0003 §Decision outcome → Pipeline | boundary/invariant | adapt | `docs/_internal/adr/0003-execution-contract-foundation.md` | Decision Outcome | N | Align with Spec→Resolution→Plan→Run terminology in plan |
| P-0002 | D2-0003 §Immutability | boundary/invariant | verbatim | `docs/_internal/adr/0003-execution-contract-foundation.md` | Decision Outcome | N | Resolution→Plan→Run immutability |
| P-0003 | D2-0003 §Decision visibility | boundary/invariant | adapt | `docs/_internal/adr/0003-execution-contract-foundation.md` | Decision Outcome | N | Align with run summary + artifacts specs |
| P-0004 | D2-0003 §Policy domains | object class | adapt | `docs/_internal/adr/0003-execution-contract-foundation.md` | Decision Outcome | N | Recast as Resolution Domains |
| P-0005 | D2-0003 §Runner vs Executor roles | boundary | verbatim | `docs/_internal/adr/0003-execution-contract-foundation.md` | Decision Outcome | N | Preserve role separation |
| P-0006 | D2-0003 §Structured findings | object class | adapt | `docs/reference/findings.md` | Finding schema | N | Schema formalized in reference spec |
| P-0007 | D2-0001 §Canonical matching basis (root-relative, POSIX) | boundary/invariant | adapt | `docs/_internal/adr/0006-paths-foundation.md` | Decision Outcome | N | POSIX-only posture per policy vCurrent |
| P-0008 | D2-0001 §Output path resolution rules | boundary/invariant | adapt | `docs/reference/path_resolution.md` | Resolution contract | N | Normalize output path rules under paths foundation |

## Guidance

- Prefer `verbatim` for definitional architecture (taxonomy, naming rules) unless the plan explicitly changes it.
- If `adapt`, record the reason in `carry_forward_matrix.md` and ensure there is no drift.
