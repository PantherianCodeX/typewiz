# typewiz

typewiz collects typing diagnostics from Pyright, mypy, and custom plugins, aggregates them into a JSON
manifest, and renders dashboards to help teams plan stricter typing rollouts.

> Status: `0.2.0` — see CHANGELOG.md for full release notes. Manifest schema, caching, and CLI are stabilized within the 0.2.x line.

## Features

- Pluggable engine architecture with Pyright and mypy built in (extend via entry points)
- Built-in incremental cache (`.typewiz_cache/cache.json`) keyed on file fingerprints and engine flags
- Deterministic diagnostics (sorted by path/line) and per-folder aggregates with actionable hints
- Exports dashboards in JSON, Markdown, and HTML for issue trackers and retros
- Captures each engine’s own summary totals (`toolSummary`) alongside parsed counts, warning when the two disagree
- Designed for CI/nightly workflows with exit codes suitable for gating builds

## Installation

Requires Python 3.12+.

```bash
pip install typewiz
```

### Local development (Python 3.12+)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[tests]
```

## Usage

Generate a manifest and dashboards (typewiz auto-detects common Python folders when `full_paths` is not configured):

```bash
typewiz audit --max-depth 3 src tests --manifest typing_audit.json
typewiz dashboard --manifest typing_audit.json --format markdown --output dashboard.md
typewiz dashboard --manifest typing_audit.json --format html --output dashboard.html
 
# fingerprinting options for large repos
typewiz audit --respect-gitignore --max-files 50000 --manifest typing_audit.json
```

Running `typewiz audit` with no additional arguments also works — typewiz will analyse the current project using its built-in Pyright and mypy defaults.

Pass extra flags to engines with `--plugin-arg runner=VALUE` (repeatable). When the value itself starts with a dash, keep the `runner=value` form to avoid ambiguity, e.g. `--plugin-arg pyright=--verifytypes`.

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

Validate a manifest against the bundled JSON Schema:

```bash
typewiz manifest validate typing_audit.json
```

### Why both Pyright and mypy?

Pyright and mypy have complementary strengths. Pyright provides fast, IDE-friendly diagnostics and excels at
detecting optional/unknown typing issues (great for readiness), while mypy’s ecosystem and plugins catch
different classes of errors and enforce strictness progressively. Running both yields broader coverage and a
clearer plan to move toward stricter typing across packages. A common pattern is:

- pyright baseline (warnings) across the monorepo, with `--strict` for green packages
- mypy for projects using mypy plugins (e.g., pydantic, SQLAlchemy), with a strict profile in those packages

### Custom engines (plugins)

Write a small class implementing the `BaseEngine` protocol and expose it via the `typewiz.engines` entry point.

```python
# examples/plugins/simple_engine.py
from collections.abc import Sequence
from dataclasses import dataclass
from typewiz.engines.base import BaseEngine, EngineContext, EngineResult
from typewiz.types import Diagnostic

@dataclass
class SimpleEngine(BaseEngine):
    name: str = "simple"
    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        return EngineResult(
            engine=self.name,
            mode=context.mode,
            command=[self.name, context.mode],
            exit_code=0,
            duration_ms=0.1,
            diagnostics=[Diagnostic(tool=self.name, severity="information", path=context.project_root/"example.py", line=1, column=1, code="S000", message="Simple", raw={})],
        )
```

Declare the entry point in your `pyproject.toml`:

```toml
[project.entry-points."typewiz.engines"]
simple = "your_package.simple:SimpleEngine"
```

Then run only your engine:

```bash
typewiz audit --runner simple
```

### Windows notes

- Paths in manifests use forward slashes for determinism; Windows paths are normalized accordingly.
- Subprocesses are invoked without shells, so argument quoting behaves consistently across OSes.
- When using `--respect-gitignore`, ensure Git is available in `PATH` on Windows.

### CI deltas

Add deltas to the compact CI line by comparing against a previous manifest:

```bash
typewiz audit --manifest typing_audit.json --compare-to last_manifest.json
```

Totals are printed along with `delta: errors=±N warnings=±N info=±N`.

### Configuration

typewiz looks for `typewiz.toml` (or `.typewiz.toml`) and validates it with a schema version header. Run `typewiz init` to scaffold a commented starter configuration, or copy `examples/typewiz.sample.toml` as a starting point.

```toml
config_version = 0

[audit]
# Let typewiz auto-detect python packages by default. Uncomment to override.
# full_paths = ["src", "tests"]
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

`include` / `exclude` lists fine-tune the directories scanned per engine, while profiles encapsulate per-engine argument sets and optional config files. Select profiles through config or via the CLI using `--profile pyright strict`.

CLI summaries stay compact by default; opt-in to richer output as needed:

```bash
typewiz audit --summary expanded --summary-fields profile,plugin-args
```

### Readiness tips

The readiness tab groups diagnostics by categories (unknownChecks, optionalChecks, unusedSymbols, general). Reduce “unknown” items first, then optional checks. Use profiles to stage enforcement per package, and verify with:

```bash
typewiz dashboard --manifest typing_audit.json --format json | jq '.tabs.readiness'
```

`--summary full` expands output and automatically includes every field (`profile`, `config`, `plugin-args`, `paths`, `overrides`).

### Folder overrides

Drop a `typewiz.dir.toml` (or `.typewizdir.toml`) inside any folder to tune engines for that subtree:

```toml
[active_profiles]
pyright = "baseline"

[engines.pyright]
plugin_args = ["--project", "pyrightconfig.pkg.json"]
include = ["."]
exclude = ["legacy"]
```

Overrides apply in addition to the root config: plugin arguments are merged and deduplicated, profiles cascade, and relative include/exclude paths are resolved from the directory containing the override file.

### Incremental caching

Each engine stores its diagnostics in `.typewiz_cache/cache.json`. The cache key captures:

- engine name and mode (`current` / `full`)
- plugin arguments and resolved command flags
- file fingerprints (mtime, size, content hash) for all scanned paths and configs

If nothing relevant changed, typewiz rehydrates diagnostics from the cache, keeping exit codes consistent while skipping the external tool invocation.

Because the cache is based on source fingerprints rather than the full Python environment, installing new plugins or
type stubs can keep stale results alive. Delete `.typewiz_cache/` after dependency or configuration changes that
alter tool behaviour to force a fresh run. Cached runs still include the upstream `toolSummary` block so manifests
capture the raw totals reported by each engine, even when served from the cache.

Every manifest entry also records the resolved engine options (`engineOptions` block) so you can trace which profile, config file, include/exclude directives, and plugin arguments produced a run.

### Logging

typewiz uses Python's standard `logging` module with the logger name `typewiz`.
Configure it in your application to capture command execution details:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("typewiz").setLevel(logging.DEBUG)
```

See the [docs](docs/typewiz.md) for detailed guidance and the export roadmap.

### Extending typewiz

Engines implement the `typewiz.engines.base.BaseEngine` protocol and are discovered through the `typewiz.engines`
entry-point group. See [`docs/typewiz.md`](docs/typewiz.md) for a minimal template and lifecycle notes.

### Python API

Use typewiz programmatically without the CLI:

```python
from pathlib import Path
from typewiz import run_audit, AuditConfig

# Minimal: discover config and run
result = run_audit(project_root=Path.cwd(), build_summary_output=True)
print(result.summary)  # dict with top folders/files and rule counts

# Advanced: override behavior
override = AuditConfig(
    full_paths=["apps", "packages"],
    skip_current=False,
    skip_full=False,
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

### Dashboards

Render dashboards from any manifest:

```bash
python -m typewiz dashboard --manifest typing_audit_manifest.json --format markdown --output typing_dashboard.md
python -m typewiz dashboard --manifest typing_audit_manifest.json --format html --view engines --output typing_dashboard.html
```

- `json` (default) – machine-readable summary with per-tab sections under `tabs.*` (overview, engines, hotspots, readiness, runs).
- `markdown` – lightweight output for issues and PR comments (mirrors the tab content with override digests and readiness notes).
- `html` – interactive report with tabs for Overview, Engine Details, Hotspots, Readiness, and Run Logs (choose the initial tab with `--view`).

When `typewiz` writes dashboards during `audit`, you can control the default HTML tab with `--dashboard-view`, and the standalone `dashboard` command mirrors the same tabs across HTML/Markdown/JSON outputs.

## Roadmap

1. **Foundation hardening** *(in progress)*
   - Make CLI outputs idempotent (rewrite dashboards even when files exist)
   - Generalise project-root discovery beyond `pyrightconfig.json` and surface clearer errors
   - Tighten engine command construction with richer typing and validation hooks
2. **Config layering & strong typing** *(done)*
   - Introduce `ProjectConfig` and `EngineSettings` models with explicit defaults and overrides
   - Support engine-specific command templates, config files, and include/exclude directives
   - Enforce schema via Pydantic 2, emitting helpful guidance for misconfiguration
3. **Profiles & execution directives** *(done)*
   - Add named profiles per engine (e.g. `pyright.strict`, `mypy.incremental`) selectable via CLI/config
   - Allow profile inheritance for quick customization (base profile + overrides)
   - Resolve active profile order: CLI > profile > engine overrides > global defaults
4. **Path-scoped configuration** *(done)*
   - Read directory/file-level overrides via `typewiz.dir.toml` to tweak runners and thresholds
   - Merge include/exclude directives per engine profile and expose overrides in manifests and dashboards
   - Add glob support for opt-in/out paths per engine and profile
5. **Dashboard experience** *(in progress)*
   - Provide tabbed HTML dashboards with compact defaults and detailed drill-down views
   - Surface override analysis, readiness (strict-ready / close / blocked), run logs, and hotspots without overwhelming the main page
   - Add CLI toggles for default dashboard views in both audit and standalone commands
   - Align JSON/Markdown outputs with tab structure for downstream tooling (including readiness metrics)
6. **Ecosystem integration**
   - Ship VS Code/IDE tasks that hydrate profiles and dashboards
   - Grow first-party engines (Pyre, Pytype) once profile API is stable
   - Prepare for PyPI release with migration guide covering new config surface
