# Typewiz Examples

This directory contains working examples demonstrating typewiz usage patterns.

## Available Examples

### [mypy-project/](mypy-project/)

Demonstrates typewiz integration with mypy's strict mode. Shows common typing issues that mypy detects and how to generate audits, dashboards, and ratchet budgets.

### [pyright-project/](pyright-project/)

Demonstrates typewiz integration with pyright's strict type checking. Highlights pyright's strengths in type narrowing, None checks, and pattern matching completeness.

## Configuration Sample

See [typewiz.sample.toml](typewiz.sample.toml) for a comprehensive configuration template with comments explaining all available options.

## Running Examples

Each example is self-contained with its own README. General pattern:

```bash
cd <example-directory>
typewiz audit src --manifest typing_audit.json
typewiz dashboard --manifest typing_audit.json --format html --output dashboard.html
```

## Requirements

- Python 3.12+
- typewiz installed (`pip install typewiz`)
