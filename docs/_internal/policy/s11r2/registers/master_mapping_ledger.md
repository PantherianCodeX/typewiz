# Master mapping ledger (sources → destinations)

This ledger is the primary evidence that nothing was lost and that no new content was invented. Keep entries granular (section/concept level), not sentence-by-sentence.

**Status codes:** see `STATUS_LEGEND.md`.

## A. Sources inventory (must be fully mapped)

| Source ID | File | Primary domains | Status |
| --- | --- | --- | --- |
| D2-0001 | `ADR-0001 Include and Exclude-draft-2.md` | include/exclude semantics; selection safety | NS |
| D2-0002 | `ADR-0002 Plugin Engines-draft-2.md` | engines; planning; equivalence | NS |
| D2-0003 | `ADR-0003 Policy Boundaries-draft-2.md` | pipeline boundaries; visibility; immutability | NS |
| D2-0004 | `ADR-0004 Taxonomy-draft-2.md` | repo taxonomy; layering; dependency direction | NS |
| D2-0005 | `ADR-0005 Naming Conventions-draft-2.md` | naming; object classes; boundary translation | NS |
| PLAN-v19 | `ADR Rewrite Plan v19.md` | authoritative rewrite deltas + gates | NS |
| SUP-0001 | `0001/path_scoping_contract.md` | path scoping details; boundary rules | NS |
| SUP-0002 | `0001/reference_implementation_outline.md` | implementation outline; scoping notes | NS |
| SUP-0003 | `0001/test_matrix.md` | scoping test coverage matrix | NS |
| SUP-0004 | `0002/execution outline.md` | engine execution sequencing outline | NS |
| SUP-0005 | `0002/test matrix.md` | engine planning/execution test coverage | NS |

### Informative / parity sources (non-authoritative, but auditable)

| Source ID | File | Used for |
| --- | --- | --- |
| CLI-H | `cli help v0.md` | CLI parity deltas tracking |
| REPO | `ratchetr-0.1.0-dev-10.zip` | repo layout validation / taxonomy sanity |

---

## B. Mapping table (section/concept level)

| Row ID | Source ID | Source anchor (heading / location) | Destination doc | Destination anchor | Type (`preserve`/`overlay`) | Status | Evidence (link/commit/PR) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
