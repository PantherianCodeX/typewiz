# Findings

**Purpose:** Define the schema and taxonomy for structured findings emitted by Resolution and Execution.
**Status:** Normative (Draft)
**Owned concepts:**

- Finding schema and severity model
- Required metadata and stability rules

**Primary links:** `docs/_internal/adr/0003-execution-contract-foundation.md`, `docs/reference/error_codes.md`, `docs/reference/identifiers.md`

## Scope

Findings are structured diagnostics emitted during Resolution, Planning, or
Execution. Findings are stable, typed records that replace unstructured notes.

## Finding schema

Required fields:

- `finding_id` (string)
- `code` (string)
- `severity` (string)
- `message` (string)
- `phase` (string)
- `subject` (object)
- `source` (object)

Optional fields:

- `data` (object)

## Field definitions

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `finding_id` | string | yes | Stable identifier; see `docs/reference/identifiers.md`. |
| `code` | string | yes | Canonical code; see `docs/reference/error_codes.md`. |
| `severity` | string | yes | `error`, `warn`, or `info`. |
| `message` | string | yes | Human-readable message (stable phrasing). |
| `phase` | string | yes | `resolution`, `planning`, or `execution`. |
| `subject` | object | yes | Subject identifiers (e.g., path token, engine name). |
| `source` | object | yes | Provenance of the finding (source kind + raw input). |
| `data` | object | no | Structured payload for tooling. |

## Severity rules

- `error` findings block the pipeline and must be surfaced in run summary.
- `warn` findings are non-fatal but must be disclosed.
- `info` findings are informational and may be suppressed from stdout, but must
  remain in artifacts.

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Defined finding schema and severity rules.
- **Preservation:** P-0006.
- **Overlay:** N/A.
- **Mapping:** MAP-0006.
- **Supersedence:** N/A.
- **Notes / risks:** Keep message text stable for tooling.
