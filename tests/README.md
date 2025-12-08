# ratchetr Test Suite

The ratchetr tests follow a pyramid-aligned layout that separates fast, deterministic unit tests from slower integration, property-based, and performance suites. The directory structure mirrors product domains to make it obvious where new coverage belongs.

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

Use the dedicated Make targets to match the subsets executed in CI:

| Suite / Goal | Make target | Equivalent pytest command |
| --- | --- | --- |
| Full CI-equivalent run | `make ci.check` | `PYTHONPATH=src pytest --cov=src/ratchetr ...` |
| Lint + typing gates | `make lint && make type` | n/a |
| Coverage-focused pytest run | `make pytest.cov` | `pytest --cov=src/ratchetr --cov-report=term --cov-fail-under=95` |
| Unit tests (fast suites under `tests/unit`) | `make pytest.unit` | `pytest tests/unit` |
| Integration workflows | `make pytest.integration` | `pytest tests/integration` |
| Property-based suites | `make pytest.property` | `pytest tests/property_based` |
| Performance benchmarks | `make pytest.performance` | `pytest tests/performance` |

Additional tips:

- Activate the repo virtualenv first: `source .venv/bin/activate`.
- Narrow scope with `pytest tests/unit/engines -k "builder"` or `pytest tests/property_based -m slow` once markers land in later phases.
- Pass `--maxfail=1` locally for quick iterations.
- CI's `quality` workflow job maps directly to these `make pytest.<category>` targets, so re-running the same subset locally reproduces any failure.

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

## Static Analysis Policy

Static analysis gates treat tests as first-class code. The same mypy/pyright strictness applies to the entire tree, and Ruff enforces every family of checks with suite-aware exceptions:

- **Common rules** – All tests must type hint fixtures/helpers and honour pytest best practices (`PT***`, `ANN***`, `ARG***`). Docstrings for test functions are optional, but module/doc coverage still applies where meaningful.
- **Unit tests** – Bare `assert` statements, sentinel magic values, and relaxed package layout warnings are ignored to keep scenarios succinct. Everything else (imports, private access, security) follows production rules.
- **Integration/performance tests** – Allowed to spawn subprocesses (`S60x`) and touch private helpers because they mimic full CLI flows. Complexity caps remain, so split scenarios into helpers when they grow beyond readability targets.
- **Property-based tests** – Hypothesis primitives such as `assume`/`reject` are exempt from boolean-argument warnings (`FBT003`), but all generated strategies must stay typed.
- **Fixtures & builders** – Dedicated helpers under `tests/fixtures/` may access private internals (`SLF001`) and carry complex setup logic (`PLR0914`). These relaxations never apply outside `tests/fixtures/`.

If a test suite truly needs to suppress an additional rule, justify it inline with `# noqa` and update this document so the rule remains discoverable. `make sec.lint` (Ruff `S` rules) runs across `tests/` as well as `src/`, while `bandit` stays scoped to `src/` to avoid assertion noise—subprocess-driven tests are already carved out via the Ruff config.

## Coverage Requirements

- Overall coverage may never drop below **95%** (validated via `make pytest.cov`).
- Each module must preserve **≥80%** line coverage; ratcheting will enforce this as suites migrate.
- When adding tests, update or create builders/stubs so future contributors can extend coverage without duplication.
- Before any commit, ensure `ruff`, `mypy`, `pyright`, and the full `pytest` suite all pass cleanly in this layout.
