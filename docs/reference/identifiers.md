# Identifiers

**Purpose:** Define stable identifiers and token/hash rules used across run artifacts.
**Status:** Normative (Draft)
**Owned concepts:**

- Stable identifiers (run_id, finding_id, engine_error_id)
- Path tokens and link-chain identifiers

**Primary links:** `docs/reference/run_summary.md`, `docs/reference/findings.md`, `docs/reference/engine_errors.md`

## Scope

Identifiers provide stable correlation across artifacts and runs. Identifiers are
opaque, stable, and not derived from user-visible text.

## Required identifiers

| Identifier | Description |
| --- | --- |
| `run_id` | Unique identifier for a command run. |
| `finding_id` | Unique identifier for a finding. |
| `engine_error_id` | Unique identifier for an engine error. |
| `path_token` | Stable identifier for a normalized path. |
| `link_chain_id` | Stable identifier for a link traversal chain. |

## Generation rules

- Identifiers are stable within a run and unique across artifacts.
- `path_token` is derived from normalized base-relative paths and is independent
  of host OS separators.

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Established identifier set and stability rules.
- **Preservation:** N/A.
- **Overlay:** N/A.
- **Mapping:** N/A.
- **Supersedence:** N/A.
- **Notes / risks:** Keep identifiers opaque; avoid embedding raw paths.
