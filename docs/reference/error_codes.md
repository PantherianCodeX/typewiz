# Error codes

**Purpose:** Define the canonical registry for stable codes used by findings and engine errors.
**Status:** Normative (Draft)
**Owned concepts:**

- Code format and stability guarantees
- Registry governance for codes

**Primary links:** `docs/reference/findings.md`, `docs/reference/engine_errors.md`

## Scope

Error codes are stable identifiers used in findings and engine errors. Codes are
versioned by meaning, not by implementation.

## Code format

- Uppercase prefix (2-4 letters) + dash + four digits, e.g., `RES-0001`.
- Prefix indicates domain: `RES` (resolution), `PLN` (planning), `EXE`
  (execution), `ENG` (engine errors), `CFG` (config), `SEL` (selectors).

## Registry rules

- Every emitted code must appear in this registry.
- Code meanings are immutable; changes require a new code.
- Deprecated codes remain listed with a replacement pointer.

## Registry (initial)

| Code | Severity | Meaning | First use |
| --- | --- | --- | --- |
| (reserved) | | Registry initialized in Phase 2. | 2025-12-20 |

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Established code format and registry governance.
- **Preservation:** P-0006 (structured findings requirement).
- **Overlay:** N/A.
- **Mapping:** MAP-0006.
- **Supersedence:** N/A.
- **Notes / risks:** Populate registry as codes are defined.
