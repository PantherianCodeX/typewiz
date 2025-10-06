## Typing Inspector

The `typing_inspector` package collects typing diagnostics from Pyright and mypy and
summarises them into a single manifest that highlights both the current enforcement surface
and the remaining work across the repository.

### Commands

Run a full audit from the repository root:

```bash
python -m typing_inspector audit --max-depth 3
```

This produces `typing_audit_manifest.json` (relative to the working directory) containing:

- All diagnostics from the current enforced configuration (`mode="current"`).
- An expansive run across the project directories (`mode="full"`).
- Aggregated per-file and per-folder summaries with recommendations for enabling stricter checks.

Options:

- `--skip-current` / `--skip-full` – limit runs to the requested modes.
- `--pyright-only` / `--mypy-only` – focus on a single tool.
- `--full-path <path>` – add directories to the full-run command.
- `--manifest <path>` – override the output location.
- `--dashboard-json`, `--dashboard-markdown`, `--dashboard-html` – write summaries in multiple formats.

### Dashboard summaries

Generate a condensed dashboard view from an existing manifest:

```bash
python -m typing_inspector dashboard --manifest typing_audit_manifest.json --format markdown --output typing_dashboard.md
python -m typing_inspector dashboard --manifest typing_audit_manifest.json --format html --output typing_dashboard.html
```

Supported formats:

- `json` (default) – machine readable summary.
- `markdown` – lightweight report for issue trackers or PR comments.
- `html` – standalone dashboard with severity totals and hotspots.

### Configuration (typing_inspector.toml)

Place a `typing_inspector.toml` in the project root or pass `--config` when running the CLI. Example:

```toml
[audit]
manifest_path = "reports/typing/manifest.json"
full_paths = ["apps", "packages"]
max_depth = 3
skip_full = false
skip_current = false
pyright_args = ["--pythonversion", "3.12"]
mypy_args = ["--strict"]
dashboard_json = "reports/typing/summary.json"
dashboard_markdown = "reports/typing/summary.md"
dashboard_html = "reports/typing/summary.html"
fail_on = "errors"
```

All CLI flags override the config file values.

### Nightly pipeline

The typing nightly workflow invokes the audit and publishes the manifest as a build artifact,
allowing progress tracking without failing the pipeline while the codebase is still being migrated.
