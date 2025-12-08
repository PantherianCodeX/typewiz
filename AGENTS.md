# Agent Instructions

## Purpose & Scope

- This file applies to the entire repository; it guides humans and AI agents alike.
- Follow these rules for all code, tests, docs, and tooling. Direct instructions in an issue/PR take precedence.

## Environment

- Use a dedicated virtualenv at `.venv` for all work; CI enforces this. Create with `python -m venv .venv` and activate it before any command.
- Prefer `make` targets (see Makefile) as the single source of truth for linting, typing, tests, packaging, and CI parity.

## Code Structure

- Use the existing src layout. Primary package lives under `src/ratchetr` and entry points under `src/ratchetr/cli`.
- Main modules orchestrate flow and I/O; helpers/utilities hold pure functions and small adapters. Do not embed business logic in CLI/arg parsing.
- Keep top-level imports fast and side-effect free. No I/O at import time.
- Use absolute imports within the package; avoid relative imports across distant modules.

## Typing & Schemas

- Typing is non-optional: annotate every function, method, variable, constant, and attribute. No `Any` except in rare, justified containment boundaries.
- Type checkers: `mypy` and `pyright` must pass in strict mode. Config is in `mypy.ini` and `pyrightconfig.json` and already strict.
- Public typing: maintain `src/ratchetr/py.typed` and run `make verifytypes` to validate exported types.
- Pydantic v2 is the canonical way to model/validate internal configuration and data interchange (see `src/ratchetr/config/models.py`).
- External/interop formats must be specified with JSON Schema (see `schemas/typing_audit_manifest.schema.json`). Keep schema and code in sync.

## Design & Patterns

- Prefer `@dataclass(slots=True)` for value objects; use `frozen=True` where immutability makes sense.
- Use `Enum`, `Literal`, `TypedDict`, `Protocol`, and `NewType` for expressive, precise types. Prefer `Final` for constants.
- Module constants are UPPER_SNAKE_CASE and typed. Expose public surface via `__all__` where helpful.
- Always start Python modules with `from __future__ import annotations`.
- Favor `pathlib.Path`, `datetime` with timezone awareness, and pure functions. Avoid ambient state; inject dependencies.
- Logging via `logging.getLogger("ratchetr")`; no `print` in library code.

## Style, Lint, Format

- Formatter: Ruff. Run `make format` (idempotent). Do not mix formatters.
- Lint: Ruff. Run `make lint` or `make lint.ruff`. The config in `pyproject.toml` will expand toward near-all rules. Treat warnings as errors.
- Keep code readable pending full rule enablement: avoid long functions, deep nesting, and large files per the limits below.

## Complexity & Size Limits

- Max function length: 60 logical lines (aim for ≤40). Split helpers early.
- Max file length: 800 logical lines (aim for ≤400). Split modules by concern.
- Cyclomatic complexity: ≤10 per function (refactor above this).
- Max arguments: ≤6 per function/method (prefer dataclasses/objects for cohesion).
- These limits are policy now and will be enforced via Ruff rules (e.g., `C901`, `PLR0912/13/15`) as configuration expands.

## Testing Standards

- Tests are mandatory for all user-visible code paths and bug fixes. Include good/bad/edge cases.
- Use `pytest` with coverage gate ≥95% (`make pytest.cov`). Property-based tests via Hypothesis for invariants (`tests/test_prop_*.py` patterns are encouraged).
- Test types of failures: invalid inputs, boundary conditions, concurrency/ordering where relevant, and golden/snapshot outputs when appropriate.
- Avoid network, time, and filesystem flakiness; use `tmp_path`, dependency injection, and deterministic seeds. No sleeps; use fakes.
- Keep tests isolated, fast, and readable. Prefer explicit fixtures in `tests/conftest.py` and factory helpers over complex fixtures.

## CI/CD

- GitHub Actions workflow in `.github/workflows/ci.yml` runs: lint, type checks (mypy + pyright), tests (with coverage), packaging validation, and optional ratchetr dashboards.
- Caching: pip, virtualenv, Ruff, mypy caches are preserved across jobs; honor these paths locally.
- The CI matrix covers Linux/macOS/Windows and Python 3.12, with 3.13 as continue-on-error. Local runs should match CI targets via `make ci.check`.

## Make Targets (preferred)

- `make ci.check` — lint, type, tests (coverage gate). CI parity.
- `make lint` / `make fix` — Ruff lint/format (check or autofix).
- `make type` — mypy + pyright strict. `make verifytypes` validates public typing.
- `make pytest.cov` — tests with coverage ≥95%.
- `make ratchetr.dashboard` — build typing dashboards. `make ratchetr.clean` clears cache.
- `make check.error-codes` — ensure exception code registry matches docs.

## Error Handling & Codes

- Raise precise, typed exceptions (see `src/ratchetr/_internal/exceptions.py`) and map to stable error codes (see `src/ratchetr/_internal/error_codes.py`).
- Keep docs synchronized with `docs/EXCEPTIONS.md`; CI enforces via `make check.error-codes`.

## Documentation

- Public modules, classes, and functions must include concise docstrings with intent, inputs/outputs, error behavior, and examples where helpful.
- Update `README.md` and `docs/` when adding commands, flags, config keys, or schemas. Prefer small, incremental docs.

## Dependencies & Security

- Keep runtime deps minimal and typed. Pin with compatible upper bounds as in `requirements*.txt`. Do not vendor dependencies.
- No secrets in code or tests. Use environment variables for keys (e.g., `RATCHETR_LICENSE_KEY`).

## Contribution Workflow

- Install pre-commit (`make ci.precommit.install`) and ensure hooks pass locally. Small, focused PRs with thorough tests and type-safety are required.
- Do not bypass typing/lint/test gates. If a temporary `# type: ignore` is unavoidable, justify it inline and add a follow-up issue.
- Keep automated checks in sync with the following special requirements:

### Code Changes

Always execute the following at the end of a code change **completion**:
Run `mypy`, `pyright`, `ruff`, and `pytest` and clear all errors without taking shortcuts.
Git commit once all are passing - no consent required - this must be completed to end the cycle.

### GIT Commit

Git commit should only be executed after all typing/linting/testing has passed.
If the commit contains code from beyond your scope, only commit your scope by default.
**IF DIRECTED TO COMMIT ALL** then investigate all changes on the repo and always git commit with a detailed, multi-line message that summarizes all code changes and when applicable the impacts or outcomes.

### Quick Start

- `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
- `pip install -r requirements-dev.txt`
- `make ci.check`

Non-negotiables: strict typing (mypy/pyright), Ruff lint/format, ≥95% coverage, `.venv` usage, Make targets, Pydantic for internal schemas, JSON Schema for external, separation of orchestration from helpers. If uncertain, prefer smaller, well-typed components with tests.
