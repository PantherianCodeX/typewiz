# Contributing to typewiz

This project uses strict typing and automated hooks to keep quality high.

## Getting started

1. Create a virtual env (Python 3.12 recommended) and install dev deps:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements-dev.txt
   ```

   Windows developers should also install GNU Make once via `choco install make -y` so the Make targets used locally and in CI are available.

2. Install pre-commit hooks:

   ```bash
   pre-commit install
   ```

3. Run hooks on all files once:

   ```bash
   pre-commit run --all-files
   ```

## What the hooks do

- Formatting and imports: Ruff (formatter + I rules)
- Linting: Ruff (with autofix)
- Typing: pyright (strict) and mypy (strict)
- Tests: `make pytest.cov` (pytest under the hood, 90% coverage gate)
- Error code sync: `make check.error-codes`

If any hook fails, fix the issues and commit again.

## VSCode setup

Recommended extensions (automatically suggested):

- Python (ms-python.python)
- Ruff (charliermarsh.ruff)

Settings applied by `.vscode/settings.json`:

- Format on save using Ruff (formatter)
- Ruff lint on save
- Enable pytest

## Common commands

```bash
make ci.check            # run lint, type checks, tests (coverage gate)
make all.lint            # lint + format check (Ruff)
make type                # mypy + pyright (strict)
make pytest.cov          # pytest with coverage ≥90%
make check.error-codes   # ensure error code registry matches docs
make verifytypes         # pyright --verifytypes for public typing
make hooks.update        # autoupdate pre-commit hook versions
```

All CI jobs invoke these targets, so running them locally ensures parity.
