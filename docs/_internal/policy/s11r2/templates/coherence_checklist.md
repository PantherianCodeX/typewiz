# Coherence Checklist (Rewrite Batch Gate)

**Purpose:** Mechanical checklist to prevent drift, duplication, and scope creep during drafting.

**Use:** Run for each rewritten ADR/spec/CLI doc before marking it ready in `registers/rewrite_status.md`.

---

## ADR checks (MADR-sized)

- [ ] MADR headings exist (Context/Problem, Decision Drivers, Considered Options, Decision Outcome, Consequences).
- [ ] ADR includes a Links section and links out for exhaustive detail.
- [ ] No inventories/grammars/default tables/schemas appear in the ADR body.
- [ ] Decision Drivers preserved or explicitly justified in the ADR’s Draft log.

## Ownership and mapping

- [ ] New/changed normative concepts have an entry in `registers/owner_index.md`.
- [ ] Draft-2 preserved/superseded/deferred concepts have rows in:
  - `registers/draft2_preservation_map.md` and
  - `registers/master_mapping_ledger.md` and
  - `registers/carry_forward_matrix.md` (verbatim vs adapted).

## Plan overlay and supersedence

- [ ] Each applied plan-v19 delta is recorded (with evidence) in `registers/plan_overlay_register.md`.
- [ ] If a delta supersedes prior content, `registers/supersedence_ledger.md` is updated with the pointers.

## Contract surfaces and parity

- [ ] CLI contract surfaces referenced by docs are consistent and up to date.
- [ ] Any CLI deltas are recorded in `registers/cli_parity_deltas.md`.

## Precision and anchors

- [ ] Clauses that will be cross-cited use stable anchors.
- [ ] No truncation markers are present in normative text (no “...” used as omission).
- [ ] If any anchor changed, `registers/anchor_changes.md` is updated.

## Drift control

- [ ] If an amendment/exception occurred, `registers/change_control.md` is updated and linked.
- [ ] Open Questions are updated (and blockers recorded) as needed in `registers/open_questions.md`.
