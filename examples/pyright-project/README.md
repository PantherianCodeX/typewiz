# Typewiz Pyright Example

This example demonstrates using typewiz to audit Python code with pyright.

## Setup

1. Ensure Python 3.12+ is installed
2. Install typewiz: `pip install typewiz`
3. Navigate to this directory: `cd examples/pyright-project`

## Running the Example

Generate a typing audit manifest:

```bash
typewiz audit src --manifest typing_audit.json
```

View the results:

```bash
# Markdown dashboard
typewiz dashboard --manifest typing_audit.json --format markdown --output dashboard.md

# HTML dashboard
typewiz dashboard --manifest typing_audit.json --format html --output dashboard.html

# Query readiness metrics
typewiz query readiness --manifest typing_audit.json --level file --format table
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
typewiz ratchet init --manifest typing_audit.json --output ratchet.json --run pyright:current --severities errors,warnings

# Enforce budget in CI
typewiz ratchet check --manifest typing_audit.json --ratchet ratchet.json
```
