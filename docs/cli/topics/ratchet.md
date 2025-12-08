# Ratchet Budgets

> Current alpha limitation: Budgets track per-file counts; per-rule and per-signature ratchets are planned for v0.2.0.

`ratchetr ratchet` manages per-file ratchet budgets derived from a manifest so teams can fail
on regressions while allowing existing debt.

Workflows:

1. `ratchetr ratchet init` — capture a baseline from a manifest into `.ratchetr/ratchet.json`.
2. `ratchetr ratchet check` — compare the latest manifest to the ratchet budget and report regressions.
3. `ratchetr ratchet update` — update the stored ratchet budgets with new totals.
4. `ratchetr ratchet rebaseline-signature` — refresh engine signature data when helpers or configurations change.
5. `ratchetr ratchet info` — inspect the current ratchet configuration and resolved budgets.

Discovery and inputs:

- `--manifest` overrides the manifest path; otherwise ratchet uses `ratchet.manifest_path` from `ratchetr.toml`.
- `--ratchet` overrides the ratchet file; otherwise it defaults to `.ratchetr/ratchet.json` or `ratchet.output_path`.
- `--run tool:mode` (repeatable) limits ratchet calculations to specific engine runs, e.g. `pyright:current`.

Budget and display controls:

- `ratchetr ratchet init --severities errors,warnings --target errors=0 --target warnings=10 --force`
  creates per-file ratchet budgets for error and warning counts and overwrites any existing ratchet file.
- `ratchetr ratchet check --format table --signature-policy fail --limit 50 --summary-only`
  compares the latest manifest against the ratchet budget and renders a table view focused on summary rows.
- `ratchetr ratchet update --target warnings=0 --force`
  refreshes stored ratchet budgets from the latest manifest while tightening the warning budget.

Use `ratchetr help ratchet` and `docs/ratchetr.md` for more details on ratchet configuration, and see
`examples/README.md` plus `examples/ratchetr.sample.toml` for end-to-end audit and ratchet workflows.
