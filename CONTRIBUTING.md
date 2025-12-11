# Contributing to ratchetr

This project uses strict typing and automated hooks to keep quality high.

## Versioning & Stability

ratchetr follows **semantic versioning** with alpha-specific semantics:

- **0.y.z-alpha**: Breaking changes allowed between minor versions
- **Schema stability**: `schemaVersion: "1"` aims for additive-only changes
- **Error codes**: Stable once documented; deprecation warnings for 6 months before removal
- **CLI flags**: May change without deprecation in 0.y.z; deprecation warnings start at v1.0+

See [ROADMAP.md](ROADMAP.md) for stability commitments per version.

## Getting started

1. Create a virtual env (Python 3.12 recommended) and install dev deps via uv:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -U pip
   pip install uv
   uv sync --extra dev
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
- Tests: `make test.cov` (pytest under the hood, 95% coverage gate)
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
make test.cov            # pytest with coverage ≥95%
make check.error-codes   # ensure error code registry matches docs
make verifytypes         # pyright --verifytypes for public typing
make hooks.update        # autoupdate pre-commit hook versions
make package.build       # build wheel + sdist via python -m build
make package.check       # run twine check on built artifacts
make package.install-test # install built wheel in a throwaway virtualenv
make package.clean        # remove build/dist artifacts
```

All CI jobs invoke these targets, so running them locally ensures parity.

## Ignore conventions (Ruff, Pylint, typing, coverage)

All suppressions are treated as exceptional and must be both:

- Narrowly scoped (single line or single file), and
- Explicitly justified in an adjacent comment.

### Per-line ignores

For any `noqa` / `pylint: disable` / `type: ignore` / `pyright: ignore[...]` used on a single line:

- Place a justification immediately above the ignored line:

  ```python
  # ignore JUSTIFIED: short, specific reason
  value = cast(SomeType, raw)  # type: ignore[assignment]
  ```

- The `ignore JUSTIFIED` line:
  - Must not include codes, only the human-readable reason.
  - Should be concise enough to stay well within the 120‑char line limit where possible.
  - Line limits include indentation and is enforced by ruff.
  - Can be single-line or multi-line reason.

### Per-file ignores

When an entire module is a deliberate special case (e.g., protocol stubs, argparse wrappers, demo examples):

- Add a short, generalized justification comment followed by the suppressions near the top of the file.
- Place block below the license with 1 blank line above and below the new block:

  ```python
  # Copyright 2025 CrownOps Engineering
  ...

  # ignore JUSTIFIED: this module mirrors argparse signatures and legitimately uses
  # Any and ellipsis stubs
  # ruff: noqa: ANN401  # pylint: disable=redundant-returns-doc,unnecessary-ellipsis

  ...
  ```

- The justification must explain why the rule does not conceptually apply to this module.

## What owns what

- Ruff:
  - Primary linter and formatter (including complexity, style, and most correctness checks).
  - We use targeted `# noqa` only for true false positives or unavoidable external APIs.
- Pylint:
  - Semantic/documentation checks (docparams, missing docstrings, structural metrics) and selected refactor hints.
- Typing (mypy/pyright):
  - `# type: ignore[...]` and `# pyright: ignore[...]` are last resorts:
    - Only for genuine false positives or unavoidable version-compat patterns.
    - Always accompanied by an `# ignore JUSTIFIED: ...` line explaining why the type checker is being overridden.
- Coverage:
  - `# pragma: no cover` is allowed for protocol/TYPE_CHECKING stubs and defensive/logging‑only branches.
  - When combined with other ignores (e.g., `unnecessary-ellipsis`), add a single `# ignore JUSTIFIED: ...` line above the stub explaining why it is excluded from coverage.

- General:
  - Use per-file `disable` for whole-module patterns (e.g., protocol stubs) where the rule(s) are not applicable to anything within the file.
  - Use per-line `disable` for all other ignores (default)

## Release Process

1. **Version Bump**: Update `version` in `pyproject.toml`
2. **CHANGELOG**: Add entry under `## Unreleased` with changes
3. **Pre-release Validation**:
   - Run `make ci.check` (all gates must pass)
   - Run `make package.build && make package.check`
4. **Git Tagging**: Create annotated tag `git tag -a v0.1.x -m \"Release v0.1.x\"`
5. **Build Artifacts**: `make package.build`
6. **Publication**: (Process TBD for first public release)
