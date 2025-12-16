# ratchetr Mypy Example

This example demonstrates using ratchetr to audit Python code with mypy.

## Setup

1. Ensure Python 3.12+ is installed
2. Install ratchetr: `pip install ratchetr`
3. Navigate to this directory: `cd examples/mypy-project`

## Running the Example

Generate a typing audit manifest:

```bash
ratchetr audit src --manifest typing_audit.json
```

View the results in different formats:

```bash
# Markdown dashboard
ratchetr dashboard --manifest typing_audit.json --format markdown --output dashboard.md

# HTML dashboard
ratchetr dashboard --manifest typing_audit.json --format html --output dashboard.html

# Query specific information
ratchetr query overview --manifest typing_audit.json --format table
ratchetr query hotspots --manifest typing_audit.json --kind files --limit 5
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
ratchetr ratchet init --manifest typing_audit.json --output ratchet.json --run mypy:current

# Check for new violations
ratchetr ratchet check --manifest typing_audit.json --ratchet ratchet.json
```
