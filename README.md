# pytc

pytc collects typing diagnostics from Pyright, mypy, and custom plugins, aggregates them into a JSON
manifest, and renders dashboards to help teams plan stricter typing rollouts.

## Features

- Pluggable runner architecture with Pyright and mypy built in (extend via entry points)
- Run configured runners in both "current" (configured scope) and "full" (repository-wide) modes
- Aggregate per-file and per-folder statistics with rule/regression hints
- Export dashboards in JSON, Markdown, and HTML for issue trackers and retros
- Designed for use in CI/nightly workflows and local audits

## Installation

```bash
pip install pytc
```

### Local development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
pip install pytest  # enable test suite
```

## Usage

Generate a manifest and dashboard:

```bash
python -m pytc audit --max-depth 3 --manifest typing_audit.json
python -m pytc dashboard --manifest typing_audit.json --format markdown --output dashboard.md
python -m pytc dashboard --manifest typing_audit.json --format html --output dashboard.html
```

### Logging

pytc uses Python's standard `logging` module with the logger name `pytc`.
Configure it in your application to capture command execution details:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("pytc").setLevel(logging.DEBUG)
```

See the [docs](docs/pytc.md) for detailed guidance and the export roadmap.

### Python API

Use pytc programmatically without the CLI:

```python
from pathlib import Path
from pytc import run_audit, AuditConfig

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
