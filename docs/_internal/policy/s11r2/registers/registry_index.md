# Registry index (canonical)

This file is the canonical list of rewrite-governance registries. Do not create duplicate registries elsewhere; add new registries here if needed.

## Core registries

- [Rewrite status](rewrite_status.md) — status/progress of required outputs
- [Owner index](owner_index.md) — one concept, one owner
- [Master mapping ledger](master_mapping_ledger.md) — source → destination mapping (section/concept level)
- [Draft-2 preservation map](draft2_preservation_map.md) — draft-2 backbone extraction list and destinations
- [Carry-forward matrix](carry_forward_matrix.md) — verbatim vs adapted carry-forward decisions
- [Plan overlay register](plan_overlay_register.md) — applied plan-v19 deltas (with evidence)
- [Supersedence ledger](supersedence_ledger.md) — what is superseded by what, and where pointers live
- [CLI parity deltas](cli_parity_deltas.md) — CLI help snapshot parity and deltas
- [Terminology map](terminology_map.md) — renames and enforcement notes
- [Open questions](open_questions.md) — blockers/ambiguities (stop-the-line)
- [Change control](change_control.md) — approved exceptions/overrides
- [Progress board](progress_board.md) — roll-up view (phase/doc/next action)

## Optional registries (as needed)

- [Roadmap register](roadmap_register.md) — deferred items with explicit promotion triggers
- [Anchor changes](anchor_changes.md) — only when anchors change

## Automation

- Progress-board roll-up is generated/updated by:
  - `scripts/docs/build_execution_contract_progress_board.py`
  - Run: `python scripts/docs/build_execution_contract_progress_board.py --write`

**Rule:** Do not hand-edit content between `<!-- GENERATED:BEGIN -->` and `<!-- GENERATED:END -->` in `progress_board.md`.
