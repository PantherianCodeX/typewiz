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

## Usage

Generate a manifest and dashboard:

```bash
python -m typing_inspector audit --max-depth 3 --manifest typing_audit.json
python -m typing_inspector dashboard --manifest typing_audit.json --format markdown --output dashboard.md
```

See the [docs](docs/typing_inspector.md) for detailed guidance and the export roadmap.
