# Querying Manifests

`typewiz query` reads an existing manifest (typically produced by `typewiz audit`)
and emits targeted slices as JSON or table output. Subcommands:

- `typewiz query overview`: severity totals, categories, and optional run summaries.
- `typewiz query hotspots`: top files or folders by diagnostic volume.
- `typewiz query readiness`: readiness buckets for follow-up action.
- `typewiz query readiness --severity error --severity warning`: restrict readiness output to specific severities.
- `typewiz query runs`: raw run metadata filtered by tool or mode.
- `typewiz query engines`: engine configuration applied to each run.
- `typewiz query rules --include-paths`: most frequent rule identifiers plus offending files.

All query subcommands require `--manifest path/to/manifest.json` and most accept
`--format json|table` plus filtering options such as `--limit` or `--status`.
