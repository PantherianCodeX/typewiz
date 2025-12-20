# Rewrite status

Track the rewrite deliverables at the artifact level. Keep this list minimal and authoritative; do not re-spec content here.

**Status codes:** see `STATUS_LEGEND.md`.

| Artifact | Canonical path (target) | Owner | Status | Last touch (YYYY-MM-DD) | Next action | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Rewrite governance policy snapshot (Policy vCurrent) | `docs/_internal/policy/s11r2-policy.md` | | DN | 2025-12-19 | Maintain stable anchors; revise only via explicit plan bump | Rewrite-only governance; not a product/runtime spec |
| Workbook + registries (governance system) | `docs/_internal/policy/s11r2/` | | DN | 2025-12-19 | Keep registry links current; avoid duplicate registries | Operational substrate (this folder) |
| ADR index (inventory) | `docs/_internal/adr/INDEX.md` | | DN | 2025-12-19 | Re-run generator after ADR file changes | Generated table must remain current |
| ADR archive folder | `docs/_internal/adr/archive/` | | DN | 2025-12-19 | Populate in Phase 7 | Immutable archive location |
| Coherence checklist | `docs/_internal/adr/COHERENCE_CHECKLIST.md` | | DN | 2025-12-19 | Run before marking any doc Ready | Mirrors `policy/s11r2/templates/coherence_checklist.md` |
| ADR index generator | `scripts/docs/generate_adr_index.py` | | DN | 2025-12-19 | Keep deterministic; no external deps | Uses `_generated_blocks.py` |
| Generated-block utility | `scripts/docs/_generated_blocks.py` | | DN | 2025-12-19 | Keep small and strict | Used by doc generators |
| CLI help snapshots (non-normative) | `docs/cli/_snapshots/` | | DN | 2025-12-19 | Refresh if CLI changes materially | Commands recorded in each snapshot |
| Internal CLI note: argv normalization | `docs/_internal/cli/argv_normalization.md` | | DN | 2025-12-19 | Expand during ADR-0003 rewrite | Implementation notes only; owner is ADR-0003 |
| Roadmap: Windows path support | `docs/_internal/roadmap/windows_paths.md` | | DN | 2025-12-19 | Expand when promoted | Explicitly roadmap-only per plan |
| Roadmap: Directory overrides | `docs/_internal/roadmap/directory_overrides.md` | | DN | 2025-12-19 | Expand when policy activates | Explicitly deferred per plan |
| Roadmap: CI candidates (doc checks) | `docs/_internal/roadmap/ci_candidates.md` | | DN | 2025-12-19 | Populate opportunistically | Non-normative recommendations |
| ADR-0001 (active rewrite) | `docs/_internal/adr/0001-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1 |
| ADR-0002 (active rewrite) | `docs/_internal/adr/0002-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1 |
| ADR-0003 (active rewrite) | `docs/_internal/adr/0003-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1; rewrite in Phase 2 |
| ADR-0004 (active rewrite) | `docs/_internal/adr/0004-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1 |
| ADR-0005 (active rewrite) | `docs/_internal/adr/0005-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1 |
| ADR-0006 (active rewrite) | `docs/_internal/adr/0006-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1; rewrite in Phase 2 |
| ADR-0007 (active rewrite) | `docs/_internal/adr/0007-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1 |
| ADR-0008 (active rewrite) | `docs/_internal/adr/0008-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1 |
| ADR-0009 (active rewrite) | `docs/_internal/adr/0009-*.md` | | NS | | Draft-2 extraction + mapping gate | Stub in Phase 1 |
| Reference specs (folder) | `docs/reference/` | | NS | | Create minimum set per plan | Stubs in Phase 1 |
| CLI contract docs (folder) | `docs/cli/` | | NS | | Create contract + inventories per plan | Topics exist; contract rewrite pending |
