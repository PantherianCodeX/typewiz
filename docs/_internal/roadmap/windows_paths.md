# Roadmap: Windows path support (non-normative)

**Owner(s):** ADR-0006 + `docs/_internal/policy/s11r2-policy.md`.

**Status:** Stub created in Phase 0. This file preserves a promotable design outline; it is not part of the normative contract until explicitly promoted by policy.

---

## Current posture (contract)

- The present-tense contract for all path-like inputs across CLI/ENV/config is **POSIX semantics**.
- Selectors remain portable canonical syntax; `\` is literal in selectors.

See: `docs/_internal/ADR Rewrite Plan v19.md` §5.5.

---

## Promotion trigger

Windows path support may only be promoted into normative ADRs/specs when:

- the execution-contract policy explicitly activates the roadmap item, and
- the relevant ADR/reference specs are updated as a coordinated change set.

---

## Design capture (to be expanded)

### 1. Input taxonomy

Capture a crisp classification of “path-like inputs” that would be impacted:

- CLI options taking paths (targets, manifests, save-as, dashboards, etc.)
- Config fields (path overrides, cache dirs, output dirs)
- ENV variables and their parsing rules
- Selector syntax (explicitly out of scope for separator changes; `\` remains literal)

### 2. Parsing and ambiguity

Document ambiguity cases and explicit disambiguation rules, including:

- drive-letter forms vs selector syntax
- UNC paths
- mixed separators

### 3. Normalization and stable outputs

Define a normalization strategy that preserves the stability rules from `docs/reference/path_resolution.md`:

- primary reporting coordinates remain normalized base-relative paths rendered with `/`
- raw host paths are not leaked unless explicitly permitted by policy

### 4. Compatibility and migration

Outline a migration posture:

- feature flag / policy activation window
- “strict by default” parsing to avoid accidental scope changes
- run-summary disclosures when Windows semantics are enabled

## Draft log

## 2025-12-20 — Phase 0 scaffolding

- **Change:** Added Phase 0 roadmap stub for Windows path support (non-normative).
- **Preservation:** N/A (Phase 0 scaffolding; no draft-2 items mapped).
- **Overlay:** N/A (no Plan v19 overlays applied).
- **Mapping:** N/A (no MAP/P/CF entries yet).
- **Supersedence:** N/A.
- **Notes / risks:** None.
