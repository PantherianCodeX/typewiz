# Path resolution

**Purpose:** Define path normalization, anchoring, and absolute gating rules.
**Status:** Normative (Draft)
**Owned concepts:**

- Base/project-root anchoring
- Normalized path rendering (POSIX)
- Absolute path gating and errors

**Primary links:** `docs/_internal/adr/0006-paths-foundation.md`, `docs/reference/identifiers.md`

## Resolution contract

### Anchors

- `base_dir` is the canonical anchor for normalized paths.
- `project_root` may be null in ad-hoc mode; base-relative paths remain valid.

### Normalization rules

- Normalize to base-relative paths with `/` separators.
- Remove `.` segments and collapse redundant separators.
- Preserve `..` segments only within allowed base boundaries; otherwise fail
  during Resolution.

### Absolute gating

- Absolute inputs are rejected unless explicitly permitted.
- Rejections emit a coded Error Finding during Resolution.

### Rendering

- Render paths in POSIX form for selectors and artifacts.
- Use `path_token` for stable identifiers (see `docs/reference/identifiers.md`).

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Defined path resolution anchors, normalization, and absolute gating.
- **Preservation:** P-0007, P-0008.
- **Overlay:** OVL-0001.
- **Mapping:** MAP-0008..MAP-0009.
- **Supersedence:** N/A.
- **Notes / risks:** Keep selector semantics in `selector_semantics.md`.
