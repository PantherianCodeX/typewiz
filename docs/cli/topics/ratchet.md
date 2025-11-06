# Ratchet Budgets

`typewiz ratchet` manages drift budgets derived from a manifest so teams can fail
on regressions while allowing existing debt.

Workflows:

1. `typewiz ratchet init` — capture a baseline from a manifest into `.typewiz/ratchet.json`.
2. `typewiz ratchet check` — compare the latest manifest to the ratchet budget.
3. `typewiz ratchet update` — update the stored budget with new totals.
4. `typewiz ratchet rebaseline-signature` — refresh signature policies when helpers change.
5. `typewiz ratchet info` — inspect the current ratchet state.

Use `--manifest` and `--ratchet` to override discovery, `--runs` to focus on specific
tool modes, and `--target` to adjust per-severity or per-run budgets.
