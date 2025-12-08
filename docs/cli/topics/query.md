# Querying Manifests

> Alpha-quality 0.1.x — query subcommands and fields are stabilising, but output shapes may gain additive fields in 0.1.x.

`ratchetr query` reads an existing manifest (typically produced by `ratchetr audit`)
and emits targeted slices as JSON or table output. All subcommands require
`--manifest path/to/typing_audit_manifest.json`.

Subcommands:

- `ratchetr query overview --manifest ...`: severity totals, with optional category and run summaries.
  - Flags: `--include-categories`, `--include-runs`, `--format json|table` (default: `json`).
- `ratchetr query hotspots --manifest ...`: top files or folders by diagnostic volume.
  - Flags: `--kind files|folders` (default: `files`), `--limit N`, `--format json|table`.
- `ratchetr query readiness --manifest ...`: readiness buckets for follow-up action.
  - Flags: `--level file|folder` (default: `folder`), `--status STATUS` (repeatable),
    `--severity error|warning|information` (repeatable), `--limit N`, `--format json|table`.
- `ratchetr query runs --manifest ...`: raw run metadata filtered by tool or mode.
  - Flags: `--tool NAME` (repeatable), `--mode current|full` (repeatable), `--limit N`, `--format json|table`.
- `ratchetr query engines --manifest ...`: engine configuration applied to each run.
  - Flags: `--limit N`, `--format json|table`.
- `ratchetr query rules --manifest ...`: most frequent rule identifiers.
  - Flags: `--limit N`, `--include-paths`, `--format json|table`.

Use `ratchetr help query` for the latest flag defaults. For manifest field details see `docs/ratchetr.md`, and for
end-to-end examples see the manifests under `examples/` (for example `examples/typing_audit_manifest.json`).
