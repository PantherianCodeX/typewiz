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
- [Status legend](STATUS_LEGEND.md) <!-- s11r2-input:status_legend --> — canonical status codes (for governance tables)

## Generated outputs (do not edit)

- [Progress board](../progress/progress_board.md) <!-- s11r2-output:progress_board --> — roll-up metrics and monitoring view
- [Dashboard](../progress/dashboard/index.html) <!-- s11r2-output:dashboard --> — static HTML view of the same metrics

## Optional registries (as needed)

- [Roadmap register](roadmap_register.md) — deferred items with explicit promotion triggers
- [Anchor changes](anchor_changes.md) — only when anchors change

## Automation

Progress outputs are generated/updated by:

- `scripts/docs/s11r2-progress.py`

The generator reads:

- `STATUS_LEGEND.md` for allowed governance status codes
- this `registry_index.md` file for input/output paths (links above)

Run from repo root:

- `python scripts/docs/s11r2-progress.py --write` (write progress board)
- `python scripts/docs/s11r2-progress.py --write-html` (write dashboard)
- `python scripts/docs/s11r2-progress.py --write --write-html` (write both)

Rules:

- Do not hand-edit files under `../progress/`.
- Edit registries under this directory, then regenerate outputs.
