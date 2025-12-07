# Typewiz Mypy Example

This example demonstrates using typewiz to audit Python code with mypy.

## Setup

1. Ensure Python 3.12+ is installed
2. Install typewiz: `pip install typewiz`
3. Navigate to this directory: `cd examples/mypy-project`

## Running the Example

Generate a typing audit manifest:

```bash
typewiz audit src --manifest typing_audit.json
```

View the results in different formats:

```bash
# Markdown dashboard
typewiz dashboard --manifest typing_audit.json --format markdown --output dashboard.md

# HTML dashboard
typewiz dashboard --manifest typing_audit.json --format html --output dashboard.html

# Query specific information
typewiz query overview --manifest typing_audit.json --format table
typewiz query hotspots --manifest typing_audit.json --kind files --limit 5
```

## Expected Diagnostics

The `typing_demo.py` file intentionally contains several typing issues that mypy will detect:

- Missing type annotations on function parameters
- Return type mismatches
- Unspecified generic types
- Missing return type annotations on methods

## Ratchet Example

Lock in current diagnostic counts to prevent regressions:

```bash
# Initialize ratchet budget
typewiz ratchet init --manifest typing_audit.json --output ratchet.json --run mypy:current

# Check for new violations
typewiz ratchet check --manifest typing_audit.json --ratchet ratchet.json
```
