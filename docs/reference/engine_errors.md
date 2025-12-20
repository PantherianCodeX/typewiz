# Engine errors

**Purpose:** Define the schema and minimum surface for engine execution failures.
**Status:** Normative (Draft)
**Owned concepts:**

- Engine error schema and minimum required fields
- Stderr is never diagnostics

**Primary links:** `docs/reference/error_codes.md`, `docs/reference/run_artifacts.md`

## Scope

Engine errors represent failures to execute a tool or process. They are distinct
from diagnostics produced by the tool itself.

## Engine error schema

Required fields:

- `engine_error_id`
- `code`
- `engine`
- `command`
- `exit_status`
- `stdio`
- `timestamp`

## Field definitions

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `engine_error_id` | string | yes | Stable identifier; see `docs/reference/identifiers.md`. |
| `code` | string | yes | Canonical code (prefix `ENG-`). |
| `engine` | string | yes | Engine name/version identifier. |
| `command` | array | yes | Executed command argv (normalized). |
| `exit_status` | integer | yes | Process exit status. |
| `stdio` | object | yes | Captured stdout/stderr metadata. |
| `timestamp` | string (RFC3339) | yes | Failure time (UTC). |

## Stderr is never diagnostics

Captured stderr is classified as engine error evidence only. Diagnostics belong
in findings emitted by parsing tool outputs, not in stderr.

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Defined engine error schema and minimum required fields.
- **Preservation:** N/A.
- **Overlay:** OVL-0003.
- **Mapping:** N/A.
- **Supersedence:** N/A.
- **Notes / risks:** Ensure diagnostics are routed through findings.
