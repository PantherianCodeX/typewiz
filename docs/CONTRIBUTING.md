# Contributing to typewiz

This project uses strict typing and automated hooks to keep quality high.

## Getting started

1. Create a virtual env (Python 3.12 recommended) and install dev deps:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements-dev.txt
   ```

2. Install pre-commit hooks:

   ```bash
   pre-commit install
   ```

3. Run hooks on all files once:

   ```bash
   pre-commit run --all-files
   ```

## What the hooks do

- Formatting: Black, isort
- Linting: Ruff (with autofix)
- Typing: pyright (strict) and mypy (strict)
- Tests: pytest

If any hook fails, fix the issues and commit again.

## VSCode setup

Recommended extensions (automatically suggested):

- Python (ms-python.python)
- Black Formatter (ms-python.black-formatter)
- Ruff (charliermarsh.ruff)

Settings applied by `.vscode/settings.json`:

- Format on save using Black
- Ruff lint on save
- Enable pytest

## Common commands

```bash
pytest -q                  # run tests
pyright -p pyrightconfig.json  # strict type checks
mypy --config-file mypy.ini     # strict type checks
```
