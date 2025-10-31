# Changelog

## v0.1.0 — 2025-10-31

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
