# Master mapping ledger (sources → destinations)

This ledger is the primary evidence that nothing was lost and that no new content was invented. Keep entries granular (section/concept level), not sentence-by-sentence.

## A. Sources inventory (must be fully mapped)

### Draft-2 ADR sources (preservation inputs)

| Source ID | File | Primary domains | Mapping status |
| --- | --- | --- | --- |
| D2-0001 | `ADR-0001 Include and Exclude-draft-2.md` | include/exclude semantics; selection safety | |
| D2-0002 | `ADR-0002 Plugin Engines-draft-2.md` | engines; planning; equivalence | |
| D2-0003 | `ADR-0003 Policy Boundaries-draft-2.md` | pipeline boundaries; visibility; immutability | |
| D2-0004 | `ADR-0004 Taxonomy-draft-2.md` | repo taxonomy; layering; dependency direction | |
| D2-0005 | `ADR-0005 Naming Conventions-draft-2.md` | naming; object classes; boundary translation | |

### Rewrite plan sources (overlay authority)

| Source ID | File | Notes | Mapping status |
| --- | --- | --- | --- |
| PLAN-v19 | `ADR Rewrite Plan v19.md` | authoritative rewrite deltas + gates | |

### Informative / parity sources (non-authoritative, but auditable)

| Source ID | File | Used for |
| --- | --- | --- |
| CLI-H | `cli help v0.md` | CLI parity deltas tracking |
| REPO | `ratchetr-0.1.0-dev8.zip` | repo layout validation / taxonomy sanity |

---

## B. Mapping table (section/concept level)

| Row ID | Source ID | Source anchor (heading / location) | Destination doc | Destination anchor | Type (`preserve`/`overlay`) | Status | Evidence (link/commit/PR) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAP-0001 | | | | | | | | |

### Status vocabulary (recommended)

- `planned`, `drafted`, `reviewed`, `accepted`, `superseded`
