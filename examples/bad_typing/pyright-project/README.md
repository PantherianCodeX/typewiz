# ratchetr Pyright Example

This example demonstrates using ratchetr to audit Python code with pyright.

## Setup

1. Ensure Python 3.12+ is installed
2. Install ratchetr: `pip install ratchetr`
3. Navigate to this directory: `cd examples/pyright-project`

## Running the Example

Generate a typing audit manifest:

```bash
ratchetr audit src --manifest .ratchetr/manifest
```

View the results:

```bash
# Markdown dashboard
ratchetr dashboard --manifest .ratchetr/manifest --format markdown --output dashboard.md

# HTML dashboard
ratchetr dashboard --manifest .ratchetr/manifest --format html --output dashboard.html

# Query readiness metrics
ratchetr query readiness --manifest .ratchetr/manifest --level file --format table
```

## Expected Diagnostics

The `typing_demo.py` file intentionally contains typing issues that pyright excels at detecting:

- Potential None access without guards
- Implicit Any types
- Type narrowing violations
- Incomplete match statements
- Overly general type annotations (e.g., bare `dict`)

## Ratchet Example

Create a typing budget to prevent regressions:

```bash
# Initialize with current state
ratchetr ratchet init --manifest .ratchetr/manifest --output ratchet.json --run pyright:current --severities errors,warnings

# Enforce budget in CI
ratchetr ratchet check --manifest .ratchetr/manifest --ratchet ratchet.json
```
