# Roadmap: documentation CI candidates (non-normative)

**Status:** Stub created in Phase 0. This file captures potential CI checks for documentation health; it does not impose requirements by itself.

---

## Candidate checks

### 1. Intra-doc link hygiene

- Validate that relative links inside `docs/` and `docs/_internal/` resolve.
- Prefer failing CI on broken internal links (reduces silent drift).

### 2. Generated artifacts are current

- Run `python scripts/docs/generate_adr_index.py --check`.
- Run `python scripts/docs/s11r2-progress.py --print` and ensure it parses (optionally run `--write` and assert working tree unchanged).

### 3. Registry table schema validation

- Validate required columns exist for each registry table (as defined by the governance policy).

### 4. Markdown formatting

- Enforce a consistent markdown linter configuration (line endings, trailing whitespace, heading style).

### 5. Drift controls

- Detect duplicate concept owners (`owner_index.md`) and fail if collisions exist.

---

## Notes

- Any CI enforcement must be adopted deliberately, with clear remediation guidance and minimal contributor friction.

## Draft log

## 2025-12-20 — Phase 0 scaffolding

- **Change:** Added Phase 0 roadmap stub for documentation CI candidates (non-normative).
- **Preservation:** N/A (Phase 0 scaffolding; no draft-2 items mapped).
- **Overlay:** N/A (no Plan v19 overlays applied).
- **Mapping:** N/A (no MAP/P/CF entries yet).
- **Supersedence:** N/A.
- **Notes / risks:** None.
