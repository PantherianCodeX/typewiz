# WORKBOOK.md — s11r2 Rewrite execution (operational checklist)

This is the shortest “do the work correctly” loop. The registries are the source of truth for progress.

---

## A. Start of a work session (5 minutes)

- [ ] Pick the target (ADR or supplementary doc).
- [ ] Update `registers/rewrite_status.md` → set status to `In progress` and set “next action”.
- [ ] Confirm concept ownership in `registers/owner_index.md` (or add it if missing).

## B. Before drafting (preservation + mapping gate)

- [ ] Identify draft-2 source items relevant to this target and add them to `registers/draft2_preservation_map.md`.
- [ ] Add source → destination rows in `registers/master_mapping_ledger.md`.
- [ ] For each draft-2 item: decide `verbatim` vs `adapted` and record in `registers/carry_forward_matrix.md`.

## C. While drafting (overlay gate)

For each applied plan-v18 delta:

- [ ] Record the delta in `registers/plan_overlay_register.md` (source anchor → targets → evidence).
- [ ] If a delta supersedes any older content, add to `registers/supersedence_ledger.md`.

## D. Draft-log and audit trail gate

- [ ] Add an entry to the doc’s “Draft log”.
- [ ] Mirror that entry into `docs/_internal/draft_logs/<doc-id>.md` (see template).

## E. “Ready for review” gate

- [ ] ADR is MADR-sized and links out (no inventories/grammars/default tables).
- [ ] Ownership is correct (no duplicate definitions).
- [ ] Draft-2 backbone items are accounted for (mapped and carried forward).
- [ ] Plan deltas are applied and logged (no untracked overlays).
- [ ] Terminology is consistent (update `registers/terminology_map.md` if you renamed anything).
- [ ] Update `registers/rewrite_status.md` → set status to `Ready for review`.

---

## Status vocabulary (recommended)

- `Not started` → `In progress` → `Ready for review` → `Approved` → `Archived/Integrated`
- Use `Blocked` only with a linked entry in `registers/open_questions.md`.

## F. Coherence pass (recommended)

- [ ] Run `templates/coherence_checklist.md`.
- [ ] If any anchors changed during edits, update `registers/anchor_changes.md`.
- [ ] If items were deferred, add them to `registers/roadmap_register.md`.
