# Changelog

## v0.1.0 — 2026-01-15

### Highlights
- First commercial release under the Typewiz Software License Agreement.
- Includes readiness dashboards, policy-ready CLI commands, manifest tooling, and cache optimisations from the prior development stream.
- Packaging, docs, and licensing reset for the new repository baseline.

### Notes
- Python 3.12+ required; all tooling is aligned with the modern typing ecosystem.
- For historical OSS releases, see the legacy history section below.

---

### Legacy history (pre-commercial reset)

#### v0.2.0 — 2025-11-05

### Added
- `typewiz query` surfaces overview, hotspot, readiness, run, engine, and rule insights without needing external filters; supports `json` and `table` output.
- Table rendering utilities provide consistent CLI formatting for list/dict payloads.

### Changed
- Tooling baseline is Python 3.12+: native `tomllib` and PEP 695 type aliases replace historical `tomli` shims.
- Requirements bumped (`pyright>=1.1.407`) to align with the Python floor.

#### v0.1.1 — 2025-11-03

### Added
- `typewiz audit --readiness` prints a post-run readiness summary without requiring a second command.
- CLI readiness helpers now accept multiple status buckets and share the same output formatting between `audit` and `readiness` subcommands.
- Extensive CLI regression tests cover summary formatting, manifest tooling, and dashboard output, keeping coverage above 90%.

### Changed
- `typewiz readiness` emits headers for each requested status and gracefully reports empty buckets.
- Coverage configuration excludes integration-heavy engine runners so pytest coverage gates reflect actionable modules.
- 3.12-only: codebase targets Python 3.12+ with `tomllib`, PEP 695 type aliases, and timezone-aware timestamps.

#### v0.1.0 — 2025-10-31

Highlights
- Cache-key hardening: include tool versions and resolved config file hash/mtime to ensure upgrades and config edits invalidate predictably.
- Faster + safer fingerprinting: reuse previous hashes when mtime/size unchanged; optional `--max-files` and `--max-fingerprint-bytes`; optional `--respect-gitignore`; avoid symlink loops.
- Manifest contract: `schemaVersion`, `toolVersions`, per-run `engineArgsEffective` and `scannedPathsResolved`; structured `engineError` for runner failures.
- CLI/CI: extended `--fail-on` to `none|warnings|errors|any`; compact totals line with optional deltas via `--compare-to`.
- Plugin ecosystem: added minimal example engine and documented entry point group `typewiz.engines`.
- JSON Schema + validator: bundled schema and `typewiz manifest validate` command; added test.
- 3.12-only: codebase targets Python 3.12+ with `tomllib`, PEP 695 type aliases, and `datetime.UTC`.

Breaking changes
- Drops Python < 3.12 compatibility.

New flags
- `--respect-gitignore`, `--max-files`, `--max-fingerprint-bytes`, `--compare-to`.

Notes
- Subprocesses are executed safely (list args, no shell). Paths are normalized for determinism.
- HTML dashboard escapes user content.

Contributors
- Thank you for feedback and testing on early releases.
