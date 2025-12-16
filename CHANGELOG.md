# Changelog

## Unreleased

- Raised the pytest coverage gate to 95% and added targeted regression tests
across cache internals, CLI ratchet helpers/commands, config models, and ratchet
core utilities to keep every module above 90% coverage.
- Documentation improvements: Added alpha status callouts, limitations section, and architecture overview to README
- Packaging cleanup: Verified alpha classifier and dependency isolation
- CONTRIBUTING consolidation: Moved to repository root with release process and versioning policy

## v0.1.0 — 2025-11-08

### Features

- **Multi-engine architecture**: Built-in Pyright and mypy runners with pluggable engine protocol via entry points
- **Manifest aggregation**: JSON manifest format (`schemaVersion: "1"`) with strict validation, capturing diagnostics, engine options, and tool summaries
- **Dashboard system**: Render summaries in JSON/Markdown/HTML with tabbed views (Overview, Engines, Hotspots, Readiness, Runs)
- **Ratchet budgets**: Per-file diagnostic budgets with signature tracking to prevent regression
- **Query commands**: `ratchetr query` subcommands for overview, hotspots, readiness, runs, engines, and rules
- **Incremental caching**: File-fingerprint-based cache (`.ratchetr_cache/cache.json`) to skip unchanged runs
- **Configuration system**: `ratchetr.toml` with engine profiles, include/exclude directives, and directory-level overrides (`ratchetr.dir.toml`)
- **CLI workflows**: `audit`, `dashboard`, `ratchet init/check/update`, `query`, `engines list`, `cache clear`, `manifest validate`

### Quality & Standards

- **95% test coverage gate**: Comprehensive unit and integration tests across all modules
- **Strict typing**: Full Pyright strict mode + mypy compliance
- **Linting & formatting**: Ruff (all rules enabled), Pylint, Bandit security scans
- **CI/CD**: GitHub Actions for tests, type checking, linting, and package builds

### Architecture

- **Schema-first design**: JSON Schema validation for manifests, ratchets, and config
- **Structured logging**: Typed logging facade with JSON output support for observability
- **Error code system**: Stable error codes documented in docs/EXCEPTIONS.md
- **Public API surface**: Clean separation between `ratchetr.api` (public) and `ratchetr._infra` (private)

### Licensing

- **Commercial distribution**: ratchetr Software License Agreement (Proprietary)
- **30-day evaluation**: Free evaluation period for internal testing
- **License key system**: `RATCHETR_LICENSE_KEY` environment variable for production use

See [README.md](README.md) for full usage documentation and [ROADMAP.md](ROADMAP.md) for future plans.
