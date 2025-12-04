# TypeWiz Test Suite

The TypeWiz tests follow a pyramid-aligned layout that separates fast, deterministic unit tests from slower integration, property-based, and performance suites. The directory structure mirrors product domains to make it obvious where new coverage belongs.

```text
tests/
├── unit/                # Domain-focused unit tests and fixtures
├── integration/         # Workflow and multi-component coverage
├── property_based/      # Hypothesis-powered invariants
├── performance/         # Benchmarks and micro/perf tests
├── fixtures/            # Shared data builders, stubs, and snapshots
└── README.md            # This file
```

## Running Tests

| Goal | Command |
| --- | --- |
| Full CI-equivalent run | `make ci.check` |
| Lint + typing gates | `make lint && make type` |
| Coverage-focused pytest run | `make pytest.cov` |
| Unit tests only | `pytest tests/unit` |
| Integration workflows | `pytest tests/integration` |
| Property-based suites | `pytest tests/property_based` |
| Performance benchmarks | `pytest tests/performance` |

Additional tips:

- Activate the repo virtualenv first: `source .venv/bin/activate`.
- Narrow scope with `pytest tests/unit/engines -k "builder"` or `pytest tests/property_based -m slow` once markers land in later phases.
- Pass `--maxfail=1` locally for quick iterations.

## Writing Tests

- Name files using the destination module followed by the behavior under test (e.g., `test_manifest_builder.py`).
- Keep functions small, deterministic, and isolated; favor pure helpers over inline fixture logic.
- Start every test module with a short docstring summarizing the system under test so the pytest collection output remains self-documenting.
- Structure test bodies using the Arrange-Act-Assert (AAA) pattern: prepare state, invoke the subject exactly once, then assert outcomes. Split scenarios via parametrization instead of chaining multiple Acts inside a single test.
- Prefer `pytest.mark.parametrize` for input matrices and Hypothesis for behavioral invariants.
- New fixtures live close to consumers: domain packages own their own `conftest.py` while shared builders live in `tests/fixtures/`.
- Avoid network, filesystem, and time dependencies unless explicitly mocked or isolated through fakes.
- Document intent with short docstrings or inline comments above complex arrangements/assertions.

## Fixture Guidelines

- `tests/conftest.py` remains reserved for global plugins and simple session fixtures.
- Domain-specific fixtures belong in that domain's `conftest.py` (e.g., `tests/unit/cli/conftest.py` once created) to prevent leakage.
- Common builders, stubs, and snapshot helpers live in `tests/fixtures/`:
  - `builders.py` gathers deterministic test-data factories (e.g., `build_diagnostic`, `build_readiness_summary`, `build_cli_summary`).
  - `stubs.py` houses typed doubles/fakes used to isolate collaborators.
  - `snapshots/` encloses golden files shared by multiple suites.
- Property-based strategies should be colocated under `tests/property_based/strategies/` and re-exported as needed.

## Coverage Requirements

- Overall coverage may never drop below **95%** (validated via `make pytest.cov`).
- Each module must preserve **≥80%** line coverage; ratcheting will enforce this as suites migrate.
- When adding tests, update or create builders/stubs so future contributors can extend coverage without duplication.
- Before any commit, ensure `ruff`, `mypy`, `pyright`, and the full `pytest` suite all pass cleanly in this layout.
