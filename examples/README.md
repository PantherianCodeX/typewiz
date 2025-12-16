# ratchetr Examples

This directory contains working examples demonstrating ratchetr usage patterns.

## Available Examples

### [mypy-project/](mypy-project/)

Demonstrates ratchetr integration with mypy's strict mode. Shows common typing issues that mypy detects and how to generate audits, dashboards, and ratchet budgets.

### [pyright-project/](pyright-project/)

Demonstrates ratchetr integration with pyright's strict type checking. Highlights pyright's strengths in type narrowing, None checks, and pattern matching completeness.

## Configuration Sample

See [ratchetr.sample.toml](ratchetr.sample.toml) for a comprehensive configuration template with comments explaining all available options.

## Running Examples

Each example is self-contained with its own README. General pattern:

```bash
cd <example-directory>
ratchetr audit src --manifest .ratchetr/manifest
ratchetr dashboard --manifest .ratchetr/manifest --format html --output dashboard.html
```

## Requirements

- Python 3.12+
- ratchetr installed (`pip install ratchetr`)
