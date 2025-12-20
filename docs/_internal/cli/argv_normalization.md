# CLI argv normalization (implementation notes)

**Owner:** ADR-0003 (Policy Boundaries / constitution).

**Status:** Stub created in Phase 0. This document is implementation guidance for the CLI boundary only; it is not a user-facing contract.

**Normative sources:**

- `docs/_internal/ADR Rewrite Plan v19.md` §5.7 (macro expansion requirements)
- `docs/cli/contract.md` (user-visible CLI contract; created in later phases)

---

## 1. Scope

This document describes the **CLI boundary normalization** step that runs **before**:

- argparse parsing / validation,
- `CommandSpec` construction, and
- any Resolution/Planning/Execution logic.

This step is deliberately constrained:

- It performs **macro expansion** and **macro-only** warnings/deduplication.
- It must **remove macro tokens** from the argv stream after expansion.
- It must not attempt to normalize or validate non-macro tokens.

---

## 2. Pipeline placement

Recommended pipeline (conceptual):

1. Raw `argv` intake
2. **Macro expansion + macro-only dedup/warnings** (this doc)
3. Normal parsing/validation (CLI contract)
4. `CommandSpec` construction (normalized tokens only)
5. Resolution → Plan → Run (ADR-0003 constitution)

---

## 3. Macro model

### 3.1 Terminology

- **Macro token:** a CLI token that triggers expansion (e.g., `--ad-hoc`).
- **Expansion:** injection of one or more *normal* tokens (e.g., `--project-root none --no-env`).
- **Macro registry:** mapping of macro token → expansion tokens.

### 3.2 Non-negotiables (from plan)

- Macro expansion is a **generalized** operation and must not be hard-coded per-flag.
- Macro expansion runs as a **boundary normalization** step.
- The macro stage is tightly scoped: **expand**, then apply **macro-only** warnings/dedup.

---

## 4. Required behavior: `--ad-hoc`

### 4.1 Expansion

`--ad-hoc` expands to:

- `--project-root none`
- `--no-env`

### 4.2 Macro-only dedup and warnings

If the user supplies `--ad-hoc` and also explicitly supplies a token that the macro injects:

- emit a warning indicating the explicit token is covered by the macro, and
- drop the macro-injected duplicate (keep the user-supplied token).

Examples (conceptual):

- `--ad-hoc --project-root none` ⇒ warn; keep the user `--project-root none`; drop macro-injected duplicate.
- `--project-root none --ad-hoc` ⇒ warn; keep the user `--project-root none`; drop macro-injected duplicate.

### 4.3 Conflict handling (non-macro validation)

Conflicts (e.g., `--project-root src --ad-hoc`) are not handled by the macro stage.
They must be detected by the **normal** parser/validator after macro expansion.

---

## 5. Warning shape (recommended)

Warnings produced by the macro stage should be structured so they can be surfaced in run summaries without ambiguity.
Recommended fields (to be aligned with `docs/reference/findings.md` in later phases):

- warning code (stable identifier)
- a short message
- the triggering macro token
- the explicit token(s) that were redundant

---

## 6. Out of scope

The macro stage must not:

- deduplicate non-macro flags,
- decide last-one-wins behavior,
- normalize aliases (e.g., `-d` vs `--dashboard`), or
- implement policy logic (ENV reads, path gating, etc.).

## Draft log

## 2025-12-20 — Phase 0 scaffolding

- **Change:** Added Phase 0 stub for argv normalization notes and guardrails.
- **Preservation:** N/A (Phase 0 scaffolding; no draft-2 items mapped).
- **Overlay:** N/A (no Plan v19 overlays applied).
- **Mapping:** N/A (no MAP/P/CF entries yet).
- **Supersedence:** N/A.
- **Notes / risks:** None.
