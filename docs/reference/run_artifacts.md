# Run artifacts

**Purpose:** Define the required artifact set and the Resolution Log schema.
**Status:** Normative (Draft)
**Owned concepts:**

- Required artifact set (composition)
- Resolution Log schema

**Primary links:** `docs/_internal/adr/0003-execution-contract-foundation.md`, `docs/reference/run_summary.md`, `docs/reference/findings.md`

## Required artifact set

Every run produces the following artifacts (logical outputs):

- Run summary
- Findings
- Resolution Log

Persistence is governed separately by write-gating rules (ADR-0007). When
persistence is suppressed, these artifacts are still produced (stdout or service
boundary) and disclosed in the run summary.

## Resolution Log schema

The Resolution Log is the detailed record of Resolution decisions. Minimum
required fields:

- `run_id`
- `timestamp`
- `command_spec`
- `policy`
- `provenance`
- `findings`

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Defined required artifact set and Resolution Log fields.
- **Preservation:** P-0003.
- **Overlay:** OVL-0002.
- **Mapping:** MAP-0003.
- **Supersedence:** N/A.
- **Notes / risks:** Keep persistence rules in ADR-0007.
