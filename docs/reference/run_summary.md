# Run summary

**Purpose:** Define the canonical run summary contract and required disclosure fields.
**Status:** Normative (Draft)
**Owned concepts:**

- Minimum required run summary fields
- Disclosure rules for modes, sources, and boundary crossings

**Primary links:** `docs/_internal/adr/0003-execution-contract-foundation.md`, `docs/reference/identifiers.md`, `docs/reference/findings.md`

## Scope

The run summary is a required artifact for every run. It is a concise, stable
contract intended for both CLI output and persisted artifacts. Detailed
resolution traces live in the Resolution Log (see `docs/reference/run_artifacts.md`).

## Required fields (minimum)

A run summary MUST include the following fields:

- `run_id`
- `timestamp`
- `command`
- `mode`
- `project_root` (or explicit `null` when disabled)
- `base_dir`
- `sources`
- `disabled_sources`
- `artifacts`
- `findings_summary`
- `status`

## Field definitions

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `run_id` | string | yes | Stable run identifier; see `docs/reference/identifiers.md`. |
| `timestamp` | string (RFC3339) | yes | Time when Resolution completed (UTC). |
| `command` | object | yes | Command name + argv summary (normalized). |
| `mode` | string | yes | `project` or `ad_hoc`. |
| `project_root` | string or null | yes | Normalized project root path, or null if disabled. |
| `base_dir` | string | yes | Normalized base directory (base-relative anchor). |
| `sources` | object | yes | Sources used (CLI/ENV/config/default). |
| `disabled_sources` | object | yes | Sources explicitly disabled and why. |
| `artifacts` | object | yes | Required artifact set and persistence status. |
| `findings_summary` | object | yes | Count of findings by severity. |
| `status` | string | yes | `success`, `failure`, or `blocked`. |

## Disclosure rules

- Boundary crossings must be reported in base-relative, POSIX-rendered paths.
- If a source is disabled (e.g., `--no-env`), only the fact of disablement and
  the disabling token are disclosed.
- If Resolution fails before Planning, `status` is `failure` and the run summary
  includes the error findings count.

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Defined required run summary fields and disclosure rules.
- **Preservation:** P-0003 (decision visibility).
- **Overlay:** OVL-0002.
- **Mapping:** MAP-0003.
- **Supersedence:** N/A.
- **Notes / risks:** Ensure Resolution Log details remain out of the summary.
