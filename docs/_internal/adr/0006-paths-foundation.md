# ADR-0006 Paths Foundation: Path system contract; normalization boundaries; base/project-root anchoring

**Purpose:** Define the path contract posture, normalization boundaries, and base/project-root anchoring rules.
**Status:** Normative (Draft)
**Owned concepts:**

- Path contract posture (POSIX-only input parsing)
- Base/project-root anchoring and normalization boundaries
- Absolute path gating policy

**Primary links:** `docs/reference/path_resolution.md`, `docs/reference/identifiers.md`

## Must not contain

- Selector semantics (owned by `docs/reference/selector_semantics.md`)
- Link traversal rules
- CLI inventories or parity tables

## Context and Problem Statement

Ratchetr must normalize and report paths consistently across inputs and outputs.
Without a strict path contract, selector evaluation and artifact rendering become
ambiguous and platform-dependent. This ADR defines the path posture and anchors
needed by Resolution and Planning.

## Decision Drivers

- Deterministic, portable path rendering.
- Clear anchoring and boundary reporting.
- Forward compatibility with future Windows input interpretation.

## Considered Options

### Option A — OS-specific parsing by default

Rejected. Platform-dependent behavior breaks portability and testability.

### Option B — POSIX-only input parsing (portable selectors)

Accepted. Policy vCurrent mandates POSIX-only path semantics for this rewrite.

## Decision Outcome

### Path contract posture

Per Policy vCurrent (`docs/_internal/policy/s11r2-policy.md`), the path contract
is POSIX-only for parsing path-like inputs. This applies to CLI, ENV, and config
inputs. Windows path interpretation is deferred to roadmap documentation.

### Normalization and anchoring

Resolution must normalize all path-like values into base-relative, POSIX-rendered
paths. The canonical coordinate system is base-relative with `/` separators.
Selectors remain portable and do not adopt OS-specific rules.

### Absolute path gating

Absolute path-like inputs are rejected unless explicitly permitted via
`--allow-absolute` / `paths.allow_absolute`. When disallowed, Resolution fails
with a coded Error Finding before Planning.

### Future-compatibility guardrail

The normalized path model must remain compatible with later Windows input
interpretation. This ADR constrains parsing only; internal identifiers and
rendering must not assume that raw inputs cannot contain `\`.

## Consequences

- Path resolution is deterministic and portable.
- Resolution provides consistent path tokens for artifacts and reporting.
- Future Windows support can be introduced without re-architecture.

## Links

- `docs/reference/path_resolution.md`
- `docs/reference/identifiers.md`
- `docs/_internal/roadmap/windows_paths.md`

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Rewrote ADR-0006 with POSIX-only posture, anchoring, and absolute gating.
- **Preservation:** P-0007, P-0008 (see CF-0007..CF-0008).
- **Overlay:** OVL-0001.
- **Mapping:** MAP-0008..MAP-0009.
- **Supersedence:** N/A.
- **Notes / risks:** Roadmap remains authoritative for Windows input semantics.
