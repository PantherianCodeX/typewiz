# typing-inspector

Typing Inspector collects typing diagnostics from Pyright and mypy, aggregates them into a JSON
manifest, and renders dashboards to help teams plan stricter typing rollouts.

## Features

- Run Pyright and mypy in both "current" (configured) and "full" (repository-wide) modes
- Aggregate per-file and per-folder statistics with rule/regression hints
- Export dashboards in JSON or Markdown for issue trackers and retros
- Designed for use in CI/nightly workflows and local audits

## Installation

```bash
pip install typing-inspector
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
python -m typing_inspector audit --max-depth 3 --manifest typing_audit.json
python -m typing_inspector dashboard --manifest typing_audit.json --format markdown --output dashboard.md
```

See the [docs](docs/typing_inspector.md) for detailed guidance and the export roadmap.

### Python API

Use typing-inspector programmatically without the CLI:

```python
from pathlib import Path
from typing_inspector import run_audit, AuditConfig

# Minimal: discover config and run
result = run_audit(project_root=Path.cwd(), build_summary_output=True)
print(result.summary)  # dict with top folders/files and rule counts

# Advanced: override behavior
override = AuditConfig(full_paths=["apps", "packages"], skip_current=False, skip_full=False, max_depth=3)
result = run_audit(project_root=Path.cwd(), override=override, write_manifest_to=Path("typing_audit_manifest.json"))

# Manifest JSON payload
manifest = result.manifest
```
