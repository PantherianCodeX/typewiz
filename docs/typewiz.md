## typewiz

The `typewiz` package collects typing diagnostics from Pyright, mypy, and other plugins and
summarises them into a single manifest that highlights both the current enforcement surface
and the remaining work across the repository.

### Commands

Run a full audit from the repository root:

```bash
python -m typewiz audit --max-depth 3
```

This produces `typing_audit_manifest.json` (relative to the working directory) containing:

- All diagnostics from the current enforced configuration (`mode="current"`).
- An expansive run across the project directories (`mode="full"`).
- Aggregated per-file and per-folder summaries with recommendations for enabling stricter checks.
- The original tool-provided summary counts (when present) under `toolSummary`, alongside the parsed totals used in `summary`. If the two diverge, typewiz logs a warning so the mismatch is visible in CI output.
- Each diagnostic preserves the engine-provided payload under `raw`, normalised to a recursive JSON value (`JSONValue`) so downstream tooling can safely consume the data without resorting to casts or `Any`.

Manifests always declare `schemaVersion = "1"` and typewiz enforces that value strictly. If you still have artefacts from older builds, regenerate them with the current `typewiz audit` command before invoking the manifest tooling.

Options:

- `--skip-current` / `--skip-full` – limit runs to the requested modes.
- `--runner <name>` – run a specific engine (repeatable; default: all registered).
- `--full-path <path>` – add directories to the full-run command.
- `--manifest <path>` – override the output location.
- `--dashboard-json`, `--dashboard-markdown`, `--dashboard-html` – write summaries in multiple formats.
- `--plugin-arg engine=ARG` – forward an argument to a specific engine (e.g. `--plugin-arg pyright=--pythonversion=3.12`).
- `--summary {compact,expanded,full}` – choose the CLI summary layout (`full` expands and shows every field).
- `--summary-fields profile,paths,overrides` – comma-separated extras to display alongside the summary (ignored when `--summary full` is used).
- `--dashboard-view overview` – set the default tab for HTML output (`overview`, `engines`, `hotspots`, or `runs`).
- `--hash-workers auto|N` – bound the number of threads used while fingerprinting files.
- `--dry-run` – execute engines and print summaries without writing manifests or dashboards.

#### Directory overrides

Place a `typewiz.dir.toml` (or `.typewizdir.toml`) within a subdirectory to scope additional configuration to that tree:

```toml
[active_profiles]
pyright = "strict"

[engines.pyright]
plugin_args = ["--project", "pyrightconfig.billing.json"]
exclude = ["legacy"]
```

Paths in `include`/`exclude` are resolved relative to the override file; engine settings and profiles are merged with the root configuration.

### Dashboard summaries

Generate a condensed dashboard view from an existing manifest:

```bash
python -m typewiz dashboard --manifest typing_audit_manifest.json --format markdown --output typing_dashboard.md
python -m typewiz dashboard --manifest typing_audit_manifest.json --format html --view engines --output typing_dashboard.html
```

- `json` (default) – machine-readable summary with tabbed sections under `tabs.*` (overview, engines, hotspots, readiness, runs).
- `markdown` – compact textual report (mirrors the tab content with override digests and readiness notes).
- `html` – interactive dashboard with tabs for Overview, Engine Details, Hotspots, Readiness, and Run Logs (`--view` chooses the initial tab).

### Ratchet budgets

Ratchets answer the “no regressions” requirement by snapshotting per-file diagnostics and reusing that budget in subsequent runs. You create, check, and refresh them entirely through the CLI:

```bash
# Generate a baseline from the latest manifest.
typewiz ratchet init \
  --manifest reports/typing/typing_audit.json \
  --output .typewiz/ratchet.json \
  --run pyright:current --severities errors,warnings --target errors=0

# Gate CI: any file that exceeds its allowance fails the step.
typewiz ratchet check \
  --manifest reports/typing/typing_audit.json \
  --ratchet .typewiz/ratchet.json

# After improvements, ratchet budgets drop automatically (never above configured targets).
typewiz ratchet update \
  --manifest reports/typing/typing_audit.json \
  --ratchet .typewiz/ratchet.json
```

Each ratchet is keyed to the tool, mode, and fully merged engine options (profile, plugin arguments, include/exclude paths, overrides, category mappings). If any of those change—for example, enabling a Ruff runner—`typewiz ratchet check` will flag a signature mismatch so you deliberately rebuild the baseline instead of silently accepting stale budgets.

### Engines & plugins

typewiz loads engines from the built-in registry (`pyright`, `mypy`) and from any entry points exposed under
the `typewiz.engines` group. Provide a custom engine by implementing the
`typewiz.engines.base.BaseEngine` protocol and declaring it in your package's `pyproject.toml`:

```toml
[project.entry-points."typewiz.engines"]
my_runner = "my_package.runners:MyRunner"
```

```python
from typing import Sequence

from typewiz.engines.base import BaseEngine, EngineContext, EngineResult
from typewiz.type_aliases import ToolName


class MyRunner(BaseEngine):
    name = "my-runner"

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        args = ["my-tool", *context.engine_options.plugin_args]
        if context.engine_options.profile:
            args.extend(["--profile", context.engine_options.profile])
        command = [*args, *paths]
        # execute subprocess here (see typewiz.engines.mypy for a template)
        tool_name = ToolName(self.name)
        return EngineResult(
            engine=tool_name,
            mode=context.mode,
            command=command,
            exit_code=0,
            duration_ms=0.0,
            diagnostics=[],
        )
```

Expose additional arguments via the CLI with `--plugin-arg my-runner=--flag` or via the TOML config `plugin_args`
section (see below).

Use `typewiz engines list` to inspect which engines were discovered (and where they came from), and `typewiz cache clear`
to remove `.typewiz_cache/` when you need to rebuild fingerprints from scratch.

#### Engine Author Guide

Engines are lightweight adapters that translate `typewiz` options into tool invocations and parse results.
Implement the following on your engine class:

- `name: str`
  - A short identifier, e.g. `"pyright"`, `"mypy"`, used in CLI flags and manifests.

- `run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult` (required)
  - Construct the external command using:
    - `context.engine_options.plugin_args`: merged/deduped args from CLI/config/profiles/overrides.
    - `context.engine_options.config_file`: resolved config path if provided.
    - `paths`: directories/files for the full run; empty for "current" mode.
  - Execute your tool (see `typewiz.engines.execution.run_pyright` / `run_mypy` as references) and return:
    - `engine`: `ToolName(self.name)`.
    - `mode`: `"current"` or `"full"`.
    - `command`: the argv used (for reproducibility and caching keys).
    - `exit_code`, `duration_ms`.
    - `diagnostics`: list of `Diagnostic` with stable path/line/column ordering.

- `category_mapping(self) -> dict[str, list[str]]` (recommended)
  - Map readiness categories to substrings of diagnostic codes for that tool, e.g.:
    - `{ "unknownChecks": ["reportUnknown", "MissingType"], "optionalChecks": ["Optional", "None"], "unusedSymbols": ["Unused", "redundant"] }`.
  - Used to drive the Readiness tab totals and recommendations; return an empty mapping if not applicable.

- `fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]` (recommended)
  - Return config files or extra inputs that should invalidate cache entries (e.g., `mypy.ini`, tool config, plugin lists).
  - Always include the resolved engine-specific config when present; return an empty list if not needed.

Best practices:

- Keep command construction deterministic (sorted paths/args when applicable) to maximize cache hits.
- Ensure diagnostics contain the original tool rule/code in `Diagnostic.code` when available.
- Prefer JSON outputs for parsing stability; when parsing text, add resilient fallbacks and tests.
- Use `EngineOptions.include`/`exclude` to honor per-engine path scoping and folder overrides.

### Configuration (typewiz.toml)

Place a `typewiz.toml` in the project root or pass `--config` when running the CLI. Example:

```toml
config_version = 0

[audit]
manifest_path = "reports/typing/manifest.json"
full_paths = ["apps", "packages"]
max_depth = 3
skip_full = false
skip_current = false
runners = ["pyright", "mypy"]
fail_on = "errors"

[audit.plugin_args]
pyright = ["--pythonversion", "3.12"]
mypy = ["--strict"]
dashboard_json = "reports/typing/summary.json"
dashboard_markdown = "reports/typing/summary.md"
dashboard_html = "reports/typing/summary.html"
```

The `config_version` field is required and validated; typewiz currently ships schema version `0`. All CLI flags
override the config file values. Per-engine arguments are merged with CLI overrides and deduplicated to ensure
stable command ordering.

### Incremental cache

Runs are cached in `.typewiz_cache/cache.json`. The cache key combines the engine name, mode, command flags, and
fingerprints (mtime, size, content hash) for all files under the configured `full_paths` and key config files
(`pyrightconfig.json`, `mypy.ini`, `typewiz.toml`). When nothing relevant changes, typewiz reuses the cached
diagnostics and exit code, dramatically reducing CI runtimes for steady-state checks.

Because the cache is derived from source fingerprints rather than the full Python environment, installing new
plugins or type stubs (for example, Django or DRF shims) may leave stale results behind. Clear `.typewiz_cache/`
after dependency or configuration changes that affect tool behaviour to force a fresh run. Cached entries now retain
the upstream `toolSummary` block so manifests from reused runs still include the raw totals reported by each engine.

### Nightly pipeline

The typing nightly workflow invokes the audit and publishes the manifest as a build artifact,
allowing progress tracking without failing the pipeline while the codebase is still being migrated.
