# ratchetr

ratchetr collects typing diagnostics from Pyright, mypy, and custom plugins,
aggregates them into a JSON manifest, and renders dashboards to help teams plan
stricter typing rollouts.

> Status: `0.1.0` — see CHANGELOG.md for full release notes. This release
> inaugurates the commercial ratchetr distribution under the ratchetr Software
> License Agreement.

## ⚠️ Alpha Status

ratchetr is **alpha-quality software (v0.1.x)**. While the core functionality is
solid and tested, expect:

- API and CLI changes between minor versions
- Dashboard layouts and features evolving
- Schemas stabilizing but not yet guaranteed stable

See [ROADMAP.md](ROADMAP.md) for stability commitments.

## Features

- Pluggable engine architecture with Pyright and mypy built in (extend via entry
  points)
- Built-in incremental cache (`.ratchetr_cache/cache.json`) keyed on file
  fingerprints and engine flags
- Deterministic diagnostics (sorted by path/line) and per-folder aggregates
  with actionable hints
- Exports dashboards in JSON, Markdown, and HTML for issue trackers and retros
- Captures each engine’s own summary totals (`toolSummary`) alongside parsed
  counts, warning when the two disagree
- Designed for CI/nightly workflows with exit codes suitable for gating builds

### Architecture

ratchetr follows a **schema-first, plugin-friendly** design:

- **Engines** (builtin or plugins) produce diagnostics
- **Manifest builder** aggregates results with strict JSON Schema validation
- **Dashboard system** renders summaries (JSON/Markdown/HTML)
- **Ratchet system** enforces per-file budgets with signature tracking

For deep-dive architecture documentation, see
[docs/ratchetr.md](docs/ratchetr.md).

## Installation

Requires Python 3.12+.

```bash
pip install ratchetr
```

### Local development (Python 3.12+)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[tests]
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding
standards, and release process.

## Usage

Generate a manifest and dashboards (ratchetr auto-detects common Python folders
when `default_paths` is not configured):

```bash
ratchetr audit --max-depth 3 src tests --manifest typing_audit.json
ratchetr dashboard --manifest typing_audit.json --format markdown --output dashboard.md
ratchetr dashboard --manifest typing_audit.json --format html --output dashboard.html

# fingerprinting options for large repos
ratchetr audit --respect-gitignore --max-files 50000 --manifest typing_audit.json
# parallelise hashing or skip writes entirely
ratchetr audit --hash-workers auto --dry-run
```

Running `ratchetr audit` with no additional arguments also works — ratchetr will
analyse the current project using its built-in Pyright and mypy defaults.

Pass extra flags to engines with `--plugin-arg runner=VALUE` (repeatable). When
the value itself starts with a dash, keep the `runner=value` form to avoid
ambiguity, e.g. `--plugin-arg pyright=--verifytypes`.

Need faster fingerprints or a quick health check? Use `--hash-workers auto|N`
to fan out hashing, and `--dry-run` to run engines without writing
manifests/dashboards (the CLI summary still prints totals for CI logs).

### Querying manifest summaries

The `ratchetr query` command exposes the most common manifest lookups
directly—no more piping through `jq` or custom scripts.

```bash
# Severity overview with per-run totals as a quick CI check (table or json)
ratchetr query overview --manifest typing_audit.json --include-runs --format table

# Top error-producing files, limited to five entries
ratchetr query hotspots --manifest typing_audit.json --kind files --limit 5

# Folder-level readiness buckets surfaced as JSON for dashboards
ratchetr query readiness --manifest typing_audit.json --level folder --status blocked --status close

# Filter runs by tool/mode to see error pressure for specific engines
ratchetr query runs --manifest typing_audit.json --tool pyright --mode current --format table

# Inspect engine profiles (plugin args, includes/excludes) captured in the manifest
ratchetr query engines --manifest typing_audit.json --format table

# Quick snapshot of the most frequent diagnostic rules
ratchetr query rules --manifest typing_audit.json --limit 10

# Include offending files per rule
ratchetr query rules --manifest typing_audit.json --include-paths --limit 5

# Filter readiness payloads by severity
ratchetr query readiness --manifest typing_audit.json --severity warning --format table
```

Each subcommand accepts `--format json` (default) or `--format table` for a
human-friendly view.

### Inspect engines and caches

Discover which engines are available (built-ins plus entry points) and clear
stale caches:

```bash
ratchetr engines list --format table
ratchetr cache clear
```

### Per-file ratchets

Lock today’s state in place and keep teams from backsliding by generating a
ratchet budget and checking it in CI:

```bash
# capture current diagnostics per file
ratchetr ratchet init --manifest typing_audit.json --output .ratchetr/ratchet.json --run pyright:current --severities errors,warnings --target errors=0

# fail builds when a file exceeds its allowance (also flags engine/profile drift)
ratchetr ratchet check --manifest typing_audit.json --ratchet .ratchetr/ratchet.json

# auto-ratchet improvements down to new baselines after fixes land
ratchetr ratchet update --manifest typing_audit.json --ratchet .ratchetr/ratchet.json
```

Ratchet files record the merged engine options (profiles, plugin args,
overrides). If the configuration for a run changes—such as adding a new plugin
or flipping profiles—the signature mismatch is called out so you can
intentionally rebuild the baseline. This keeps future engines like Ruff aligned
with the budgets you enforce today.

The on-disk format is documented in `schemas/ratchet.schema.json`, so you can
validate, transform, or ingest ratchet budgets with your own tooling.

### Typing & CI

Type checking locally:

```bash
# mypy (Python typing)
mypy --config-file mypy.ini

# pyright (complementary checker)
pyright -p pyrightconfig.json
```

Standardized via tox:

```bash
# run unit tests
tox -e py312

# run static typing checks
tox -e mypy,pyright


```

In CI, a GitHub Actions workflow (`.github/workflows/ci.yml`) runs tests and both type checkers on every push/PR.

### Bulk import rewrites

When files move between packages you can rewrite imports en masse with the helper
script. By default it respects `.gitignore`/tracked files (it uses `git ls-files`
under the hood), so temporary or vendor folders aren’t touched unless you opt out:

```bash
# quick ad-hoc mapping
python scripts/refactor_imports.py --map ratchetr.logging_utils=ratchetr.logging --map ratchetr._internal.exceptions=ratchetr.exceptions

# store large migrations in a file
cat > mappings.txt <<'EOF'
ratchetr.logging_utils=ratchetr.logging
ratchetr._internal.exceptions=ratchetr.exceptions
EOF
python scripts/refactor_imports.py --mapping-file mappings.txt --apply

# insert missing imports or update __all__ entries
python scripts/refactor_imports.py \
  --ensure-import src/ratchetr/api.py:ratchetr.runtime:new_helper \
  --export-map run_audit=execute_audit \
  --apply
```

It only touches `import`/`from` statements under `src/` by default; pass
`--root .` to include other folders (tests/docs/etc.).

### Public shims (runtime/helpers)

Downstream code should import shared helpers from the supported shims instead of
the private `_internal` modules. The stable surfaces are:

- `ratchetr.runtime` for JSON/command helpers and path resolution utilities.
- `ratchetr.logging` for CLI logging setup.
- `ratchetr.exceptions` and `ratchetr.error_codes` for structured error handling.
- `ratchetr.cache` and `ratchetr.collections` for cache helpers and dedupe utilities.

These modules are what the CLI and services layer use today; importing directly
from `ratchetr._internal` is blocked in CI and will fail guardrail tests.

Validate a manifest against the bundled JSON Schema:

```bash
ratchetr manifest validate typing_audit.json
```

Manifests must declare `schemaVersion` `"1"` exactly; older payloads or files missing the field now fail fast instead of being upgraded implicitly. Re-run `ratchetr audit` to regenerate manifests before running query/ratchet commands if your artefacts predate the current schema.

### Why both Pyright and mypy?

Pyright and mypy have complementary strengths. Pyright provides fast,
IDE-friendly diagnostics and excels at detecting optional/unknown typing issues
(great for readiness), while mypy’s ecosystem and plugins catch different
classes of errors and enforce strictness progressively. Running both yields
broader coverage and a clearer plan to move toward stricter typing across
packages. A common pattern is:

- pyright baseline (warnings) across the monorepo, with `--strict` for green
  packages
- mypy for projects using mypy plugins (e.g., pydantic, SQLAlchemy), with a
  strict profile in those packages

### Exception References

A catalog of exceptions with stable error codes is available in
docs/EXCEPTIONS.md: see how to catch precise error types and map them to codes
for logs or CI.

## Limitations (Alpha)

Current alpha limitations:

- **Python-only engines**: Only mypy and pyright built-in (other languages
  planned for v0.3.0+)
- **File-level ratchets**: Budgets track per-file counts; per-rule and
  per-signature ratchets coming in v0.2.0
- **Dashboard optimization**: HTML dashboards work best with <10k diagnostics;
  large manifest support improving
- **Schema evolution**: `schemaVersion: "1"` is stabilizing but may have
  additive changes in 0.1.x releases

See [ROADMAP.md](ROADMAP.md) for planned improvements.

## Licensing

ratchetr is distributed under the **Apache License, Version 2.0**.

See [`LICENSE`](./LICENSE) for the full agreement
and summary. For custom development and support, contact
**<crownops-eng@pm.me>**.

### Custom engines (plugins)

Write a small class implementing the `BaseEngine` protocol and expose it via
the `ratchetr.engines` entry point.

```python
# examples/plugins/simple_engine.py
from collections.abc import Sequence
from dataclasses import dataclass
from ratchetr.engines.base import BaseEngine, EngineContext, EngineResult
from ratchetr.core.model_types import SeverityLevel
from ratchetr.type_aliases import ToolName
from ratchetr.types import Diagnostic

@dataclass
class SimpleEngine(BaseEngine):
    name: str = "simple"
    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        tool_name = ToolName(self.name)
        return EngineResult(
            engine=tool_name,
            mode=context.mode,
            command=[self.name, context.mode],
            exit_code=0,
            duration_ms=0.1,
            diagnostics=[
                Diagnostic(
                    tool=tool_name,
                    severity=SeverityLevel.INFORMATION,
                    path=context.project_root / "example.py",
                    line=1,
                    column=1,
                    code="S000",
                    message="Simple",
                    raw={},
                )
            ],
        )
```

Built-in adapters live under `ratchetr.engines.builtin` (see `pyright` and
`mypy`) and are good templates for production plugins. Higher layers
(CLI/services) consume public modules such as `ratchetr.runtime` and
`ratchetr.logging`; direct imports from
`ratchetr._internal` are disallowed and enforced via tests.

Declare the entry point in your `pyproject.toml`:

```toml
[project.entry-points."ratchetr.engines"]
simple = "your_package.simple:SimpleEngine"
```

Then run only your engine:

```bash
ratchetr audit --runner simple
```

### Windows notes

- Paths in manifests use forward slashes for determinism; Windows paths are
  normalized accordingly.
- Subprocesses are invoked without shells, so argument quoting behaves
  consistently across OSes.
- When using `--respect-gitignore`, ensure Git is available in `PATH` on
  Windows.

### CI deltas

Add deltas to the compact CI line by comparing against a previous manifest:

```bash
ratchetr audit --manifest typing_audit.json --compare-to last_manifest.json
```

Totals are printed along with `delta: errors=±N warnings=±N info=±N`.

### Configuration

ratchetr looks for `ratchetr.toml` (or `.ratchetr.toml`) and validates it with a
schema version header. Run `ratchetr init` to scaffold a commented starter
configuration, or copy `examples/ratchetr.sample.toml` as a starting point.

```toml
config_version = 0

[audit]
# Let ratchetr auto-detect python packages by default. Uncomment to override.
# default_paths = ["src", "tests"]
runners = ["pyright", "mypy"]
fail_on = "errors"
```

The schema is stabilised via Pydantic 2; bumping `config_version` will reject outdated configs with a clear error.

Layer engine-level settings and reusable profiles:

```toml
[audit.active_profiles]
pyright = "strict"

[audit.engines.pyright]
plugin_args = ["--pythonversion", "3.12"]
include = ["packages/api"]

[audit.engines.pyright.profiles.strict]
inherit = "baseline"
plugin_args = ["--strict"]
config_file = "configs/pyright-strict.json"

[audit.engines.pyright.profiles.baseline]
plugin_args = ["--warnings"]
exclude = ["packages/legacy"]
```

`include` / `exclude` lists fine-tune the directories scanned per engine, while
profiles encapsulate per-engine argument sets and optional config files. Select
profiles through config or via the CLI using `--profile pyright strict`.

CLI summaries stay compact by default; opt-in to richer output as needed:

```bash
ratchetr audit --summary expanded --summary-fields profile,plugin-args
```

### Readiness tips

The readiness tab groups diagnostics by categories (unknownChecks,
optionalChecks, unusedSymbols, general). Reduce “unknown” items first, then
optional checks. Use profiles to stage enforcement per package, and verify
with:

```bash
ratchetr dashboard --manifest typing_audit.json --format json | jq '.tabs.readiness'
```

`--summary full` expands output and automatically includes every field
(`profile`, `config`, `plugin-args`, `paths`, `overrides`).

When you want a quick console view, run the audit with the readiness switch:

```bash
ratchetr audit src --readiness --readiness-status blocked --readiness-status ready
```

This prints the top offenders for each requested bucket immediately after the
audit completes. Use `--readiness-level file` for per-file output or bump
`--readiness-limit` to see a larger slice.

The standalone readiness command mirrors the new behaviour:

```bash
ratchetr readiness --manifest typing_audit.json --status blocked --status ready
```

It now accepts multiple `--status` arguments, renders headers for every bucket, and reports `<none>` when a bucket is empty so the output stays informative in CI logs. Pair it with `--severity error --severity warning` to focus on high-signal findings, and `--details` to include per-entry severity counts.

### Folder overrides

Drop a `ratchetr.dir.toml` (or `.ratchetrdir.toml`) inside any folder to tune engines for that subtree:

```toml
[active_profiles]
pyright = "baseline"

[engines.pyright]
plugin_args = ["--project", "pyrightconfig.pkg.json"]
include = ["."]
exclude = ["legacy"]
```

Overrides apply in addition to the root config: plugin arguments are merged and
deduplicated, profiles cascade, and relative include/exclude paths are resolved
from the directory containing the override file.

### Incremental caching

Each engine stores its diagnostics in `.ratchetr_cache/cache.json`. The cache key captures:

- engine name and mode (`current` / `target`)
- plugin arguments and resolved command flags
- file fingerprints (mtime, size, content hash) for all scanned paths and configs

If nothing relevant changed, ratchetr rehydrates diagnostics from the cache, keeping exit codes consistent while skipping the external tool invocation.

Because the cache is based on source fingerprints rather than the full Python
environment, installing new plugins or type stubs can keep stale results
alive. Delete `.ratchetr_cache/` after dependency or configuration changes that
alter tool behaviour to force a fresh run. Cached runs still include the
upstream `toolSummary` block so manifests capture the raw totals reported by
each engine, even when served from the cache.

Set `RATCHETR_HASH_WORKERS=auto` (or a positive integer) to parallelise
fingerprint hashing across threads when large projects need faster cache
refreshes. Leave it unset to keep the default sequential strategy.

Every manifest entry also records the resolved engine options (`engineOptions`
block) so you can trace which profile, config file, include/exclude
directives, and plugin arguments produced a run.

### Logging

ratchetr exposes a dedicated logging façade so CLI runs, engines, ratchets, and
dashboards all emit consistent, structured records. Configure it once and wire
the output into your collector:

```python
from ratchetr.logging import configure_logging, structured_extra
from ratchetr.core.model_types import LogComponent

# CLI flags take precedence, then environment variables, then these defaults.
configure_logging(log_format="json", log_level="info")
logger = logging.getLogger("ratchetr")
logger.info(
    "ratchetr audit starting",
    extra=structured_extra(component=LogComponent.CLI, details={"runs": 2}),
)
```

- `--log-format` / `RATCHETR_LOG_FORMAT` (`text`, `json`)
- `--log-level` / `RATCHETR_LOG_LEVEL` (`debug`, `info`, `warning`, `error`)

`structured_extra` enforces the typed payload used throughout the CLI so
downstream tooling can rely on fields such as `component`, `tool`, `mode`,
`duration_ms`, `counts`, `cached`, and `exit_code`.

Sample JSON line (truncated for brevity):

```json
{
  "timestamp": "2025-01-12T12:12:01.234567+00:00",
  "level": "info",
  "logger": "ratchetr.audit.execution",
  "message": "Running pyright:current (pyright --outputjson ...)",
  "component": "cli",
  "tool": "pyright",
  "mode": "current",
  "duration_ms": 812.4,
  "exit_code": 0
}
```

See the [docs](docs/ratchetr.md) for a full breakdown of components and fields.

### Extending ratchetr

Engines implement the `ratchetr.engines.base.BaseEngine` protocol and are
discovered through the `ratchetr.engines` entry-point group. See
[`docs/ratchetr.md`](docs/ratchetr.md) for a minimal template and lifecycle
notes.

### Python API

Use ratchetr programmatically without the CLI:

```python
from pathlib import Path
from ratchetr import run_audit, AuditConfig

# Minimal: discover config and run
result = run_audit(project_root=Path.cwd(), build_summary_output=True)
print(result.summary)  # dict with top folders/files and rule counts

# Advanced: override behavior
override = AuditConfig(
    default_paths=["apps", "packages"],
    skip_current=False,
    skip_target=False,
    max_depth=3,
    dashboard_html=Path("reports/typing/summary.html"),
)
result = run_audit(
    project_root=Path.cwd(),
    override=override,
    write_manifest_to=Path("typing_audit_manifest.json"),
    build_summary_output=True,
)
print(result.summary["topFolders"][:3])

# Manifest JSON payload
manifest = result.manifest
```

### Public API (`ratchetr.api`)

The `ratchetr.api` module re-exports the high-level orchestration helpers so you can script audits,
dashboards, and manifest validation without digging into internal packages.

```python
from pathlib import Path

from ratchetr import AuditConfig
from ratchetr.api import (
    build_summary,
    render_markdown,
    run_audit,
    validate_manifest_file,
)

audit = AuditConfig(default_paths=["src"])
result = run_audit(project_root=Path.cwd(), override=audit, build_summary_output=True)

# Render a markdown summary (build one if the audit skipped it)
summary = result.summary or build_summary(result.manifest)
print(render_markdown(summary))

# Validate the manifest output (JSON Schema if `jsonschema` is installed)
manifest_path = Path("typing_audit_manifest.json")
validation = validate_manifest_file(manifest_path)
assert validation.is_valid, validation.payload_errors
```

### Dashboards

Render dashboards from any manifest:

```bash
python -m ratchetr dashboard --manifest typing_audit_manifest.json --format markdown --output typing_dashboard.md
python -m ratchetr dashboard --manifest typing_audit_manifest.json --format html --view engines --output typing_dashboard.html
```

- `json` (default) – machine-readable summary with per-tab sections under `tabs.*` (overview, engines, hotspots, readiness, runs).
- `markdown` – lightweight output for issues and PR comments (mirrors the tab content with override digests and readiness notes).
- `html` – interactive report with tabs for Overview, Engine Details, Hotspots, Readiness, and Run Logs (choose the initial tab with `--view`).

When `ratchetr` writes dashboards during `audit`, you can control the default HTML tab with `--dashboard-view`, and the standalone `dashboard` command mirrors the same tabs across HTML/Markdown/JSON outputs.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development roadmap.

**Next milestones**:

- **v0.2.0**: Per-rule/per-signature ratchets, additional engines (Pylint, Ruff), VS Code extension
- **v0.3.0**: Cross-language support (TypeScript, Kotlin, C++), monorepo features
- **v1.0+**: Enterprise features, advanced analytics, HTTP API

### Manifest validation and schema

ratchetr includes a Pydantic-backed manifest validator and a CLI to emit the JSON Schema:

- Validate an existing manifest file:

  `ratchetr manifest validate path/to/manifest.json`

  If the optional `jsonschema` package is available, the CLI also validates against the
  generated schema and reports any schema errors.

- Emit the manifest JSON Schema:

  `ratchetr manifest schema --output schemas/typing-manifest.schema.json`

Programmatic validation is available via `ratchetr.api.validate_manifest_file` (payload plus optional
JSON Schema) or the lower-level `ratchetr.manifest_models.validate_manifest_payload`. Validation errors
raise `RatchetrValidationError` with access to the underlying Pydantic `ValidationError` for detailed
diagnostics.

### Exception Reference

ratchetr exposes a small, precise exception hierarchy to enable robust error handling.

- `ratchetr.RatchetrError` (base): Base class for all Ratchetr-specific exceptions.
- `ratchetr.RatchetrValidationError`: Raised for validation failures (e.g., manifest or config parsing).
- `ratchetr.RatchetrTypeError`: Raised when runtime inputs have invalid types.

Config-specific exceptions (raised from `ratchetr.config`):

- `ConfigValidationError`: Base for config validation issues.
- `ConfigFieldTypeError`: Field has the wrong type (e.g., `fail_on` not a string).
- `ConfigFieldChoiceError`: Field value not among allowed choices (e.g., `fail_on`).
- `UndefinedDefaultProfileError`: Default profile not found among declared profiles.
- `UnknownEngineProfileError`: Active profile references an unknown engine profile.
- `UnsupportedConfigVersionError`: Config declares an unsupported schema version.
- `ConfigReadError`: Underlying I/O failure reading a config file.
- `DirectoryOverrideValidationError`: Invalid directory override file.
- `InvalidConfigFileError`: Invalid top-level config file.

Dashboard:

- `DashboardTypeError`: Unexpected types in readiness/dashboard inputs.

Manifest:

- `ManifestValidationError`: Wraps a Pydantic `ValidationError` for manifest payloads.

Example usage:

```python
from ratchetr import RatchetrValidationError
from ratchetr.config import load_config

try:
    cfg = load_config()
except RatchetrValidationError as exc:
    # Handle or log validation details
    print("Config invalid:", exc)
```

## Make Targets

Use the Makefile to run common workflows with consistent settings:

- Lint & format
  - `make lint` – Ruff lint + format check
  - `make check.error-codes` – Verify error code registry matches documentation

- Typing
  - `make type` – Run mypy + pyright
  - `make verifytypes` – Run pyright `--verifytypes` for API contracts

- Tests
  - `make test` – Run pytest (all tests)
  - `make test.verbose`
  - `make test.failfast`
  - `make test.unit` / `make test.integration` / `make test.property` / `make test.performance`
  - `make test.cov` – Run tests with coverage (enforces ≥95%)
- Benchmarks
  - `make test.bench` – Run readiness/aggregate benchmarks (skips if `pytest-benchmark` is unavailable)

- Packaging
  - `make package.build` – Build sdist and wheel into `dist/`
  - `make package.check` – Run `twine check` on the built artifacts
  - `make package.install-test` – Install the wheel into a temporary venv to confirm installability
  - `make package.clean` – Remove `dist/`, `build/`, and egg-info artifacts

- CI aggregate
  - `make ci.check` – Lint, type checks, and tests

- Hooks & maintenance
  - `make hooks.update` – Autoupdate pinned pre-commit hook versions

Run `make help` for grouped help and `make <group>.help` for a subset (e.g., `tests.help`).
