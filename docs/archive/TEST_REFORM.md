# TypeWiz Test Suite Reorganization Plan

## Executive Summary

**Current State**: 45 test files (~321 tests) in a flat directory structure
**Target State**: Hierarchical organization by test type and domain with clear separation of concerns
**Timeline**: 7 phases with incremental migration
**Success Criteria**: 90%+ coverage maintained, all tests passing, improved maintainability

---

## Current State Analysis

### Test Statistics

- **Total test files**: 45 files (44 unit test files + 1 perf benchmark directory)
- **Total test functions**: 321 tests
- **Total test lines**: 8,402 lines across all test files
- **Largest test file**: test_cli.py (38 tests, 46KB)
- **Testing frameworks**: pytest >= 8.4.0, pytest-benchmark, pytest-cov, hypothesis

### Current Directory Structure

```text
tests/
├── conftest.py                  # Global fixtures
├── snapshots/                   # 2 snapshot files (dashboard HTML/markdown)
├── perf/                        # Performance benchmarks
│   └── test_benchmarks.py
└── test_*.py                    # 44 test files (flat structure)
```

### Test Distribution by Domain

- **CLI Tests**: 7 files (~130 tests)
- **Configuration & Validation**: 2 files (~38 tests)
- **API & Core Functionality**: 2 files (~20 tests)
- **Engine Tests**: 4 files (~25 tests)
- **Manifest/Data Structure**: 3 files (~20+ tests)
- **Readiness Assessment**: 2 files (~13 tests)
- **Ratchet (Regression Prevention)**: 4 files (~23 tests)
- **Cache & Internal**: 3 files (~25 tests)
- **Utilities & Helpers**: 3 files (~42 tests)
- **Model & Type Tests**: 2 files (~15 tests)
- **Other Features**: 8 files (~various)
- **Property-Based Tests**: 4 files (using @hypothesis.given)
- **Performance Tests**: 1 directory (2 benchmarks)

### Current Issues

1. **Flat file structure**: 45 test files in a single directory without subdirectories
2. **Mixed test types**: Unit, integration, property-based, and performance tests not separated
3. **No test categorization by module domain**: Tests for related modules scattered across multiple files
4. **No test fixtures isolation**: Fixtures shared across all tests in conftest.py without domain-specific ones
5. **Inconsistent naming**: Some files use prefixes like `test_prop_*` but no consistent pattern for other types

---

## Phase 1: Foundation & Structure (Prerequisites)

### 1.1 Create New Directory Structure

Create the following hierarchical structure:

```text
tests/
├── conftest.py                          # Global fixtures only
├── unit/                                # Pure unit tests (isolated, fast)
│   ├── conftest.py                      # Unit test fixtures
│   ├── api/                             # API domain tests
│   │   └── __init__.py
│   ├── cli/                             # CLI domain tests
│   │   ├── __init__.py
│   │   └── commands/
│   │       └── __init__.py
│   ├── config/                          # Configuration tests
│   │   └── __init__.py
│   ├── engines/                         # Engine tests
│   │   └── __init__.py
│   ├── manifest/                        # Manifest tests
│   │   └── __init__.py
│   ├── readiness/                       # Readiness assessment tests
│   │   └── __init__.py
│   ├── ratchet/                         # Ratchet feature tests
│   │   └── __init__.py
│   ├── cache/                           # Cache tests
│   │   └── __init__.py
│   ├── utilities/                       # Utility function tests
│   │   └── __init__.py
│   ├── models/                          # Model and type tests
│   │   └── __init__.py
│   └── misc/                            # Miscellaneous tests
│       └── __init__.py
├── integration/                         # Integration tests (multiple components)
│   ├── conftest.py                      # Integration test fixtures
│   └── workflows/
│       └── __init__.py
├── property_based/                      # Hypothesis property-based tests
│   ├── conftest.py                      # Hypothesis fixtures
│   └── strategies/
│       └── __init__.py
├── performance/                         # Benchmark tests
│   ├── conftest.py                      # Benchmark fixtures
│   └── benchmarks/
│       └── __init__.py
├── fixtures/                            # Shared test data & utilities
│   ├── __init__.py
│   ├── builders.py                      # Test data builders
│   ├── snapshots/                       # Snapshot files
│   └── stubs.py                         # Mock objects
└── README.md                            # Testing documentation
```

### 1.2 Create Testing Documentation

Create `tests/README.md` with:

- Overview of test organization
- How to run different test categories
- Test writing conventions
- Fixture usage guidelines
- Coverage requirements

---

## Phase 2: Categorize & Refactor Tests

### 2.1 Unit Tests Migration Map

**API Domain** (`tests/unit/api/`)

- `test_api.py` → `tests/unit/api/test_api.py`
- `test_api_helpers.py` → `tests/unit/api/test_api_helpers.py`

**CLI Domain** (`tests/unit/cli/`)

- `test_cli_helpers.py` → `tests/unit/cli/test_helpers.py`
- `test_cli_help_command.py` → `tests/unit/cli/test_help_command.py`
- `test_cli_ratchet_helpers.py` → `tests/unit/cli/test_ratchet_helpers.py`
- `test_cli_commands_ratchet.py` → `tests/unit/cli/commands/test_ratchet.py`
- `test_cli_commands_cache.py` → `tests/unit/cli/commands/test_cache.py`
- `test_cli_commands_manifest.py` → `tests/unit/cli/commands/test_manifest.py`

**Configuration Domain** (`tests/unit/config/`)

- `test_config.py` → `tests/unit/config/test_config.py`
- `test_data_validation.py` → `tests/unit/config/test_validation.py`
- `test_audit_options.py` → `tests/unit/config/test_audit_options.py`

**Engines Domain** (`tests/unit/engines/`)

- `test_engines_base.py` → `tests/unit/engines/test_base.py`
- `test_engines_builtin.py` → `tests/unit/engines/test_builtin.py`
- `test_engines_registry.py` → `tests/unit/engines/test_registry.py`
- `test_engines_execution.py` → `tests/unit/engines/test_execution.py`

**Manifest Domain** (`tests/unit/manifest/`)

- `test_manifest_schema.py` → `tests/unit/manifest/test_schema.py`
- `test_manifest_builder.py` → `tests/unit/manifest/test_builder.py`

**Readiness Domain** (`tests/unit/readiness/`)

- `test_readiness.py` → `tests/unit/readiness/test_readiness.py`
- `test_readiness_views.py` → `tests/unit/readiness/test_views.py`

**Ratchet Domain** (`tests/unit/ratchet/`)

- `test_ratchet.py` → `tests/unit/ratchet/test_ratchet.py`
- `test_ratchet_io.py` → `tests/unit/ratchet/test_io.py`
- `test_ratchet_schema.py` → `tests/unit/ratchet/test_schema.py`
- `test_ratchet_summary.py` → `tests/unit/ratchet/test_summary.py`
- `test_services_ratchet.py` → `tests/unit/ratchet/test_services.py`

**Cache Domain** (`tests/unit/cache/`)

- `test_cache_hashing.py` → `tests/unit/cache/test_hashing.py`
- `test_cache_invalidation.py` → `tests/unit/cache/test_invalidation.py`
- `test_internal_cache.py` → `tests/unit/cache/test_internal.py`

**Utilities Domain** (`tests/unit/utilities/`)

- `test_utils.py` → `tests/unit/utilities/test_utils.py`
- `test_logging_utils.py` → `tests/unit/utilities/test_logging.py`
- `test_common_override_utils.py` → `tests/unit/utilities/test_overrides.py`
- `test_error_codes.py` → `tests/unit/utilities/test_error_codes.py`

**Models Domain** (`tests/unit/models/`)

- `test_model_type_enums.py` → `tests/unit/models/test_enums.py` (non-property tests)
- `test_types_unit.py` → `tests/unit/models/test_types.py`

**Miscellaneous** (`tests/unit/misc/`)

- `test_aggregate.py` → `tests/unit/misc/test_aggregate.py`
- `test_dashboard.py` → `tests/unit/misc/test_dashboard.py`
- `test_import_guardrails.py` → `tests/unit/misc/test_import_guardrails.py`
- `test_internal_package.py` → `tests/unit/misc/test_internal_package.py`
- `test_license.py` → `tests/unit/misc/test_license.py`
- `test_main_entrypoint.py` → `tests/unit/misc/test_main.py`
- `test_refactor_imports.py` → `tests/unit/misc/test_refactor_imports.py`
- `test_runner.py` → `tests/unit/misc/test_runner.py`

### 2.2 Integration Tests Refactoring

**Extract from test_cli.py** (38 tests, 46KB):

- Analyze and split into:
  - Unit tests → `tests/unit/cli/test_cli_core.py` (isolated CLI parsing/validation)
  - Integration tests → `tests/integration/workflows/test_cli_workflows.py` (full command execution)

**Create new integration test categories**:

- `tests/integration/workflows/test_end_to_end.py` - Full audit workflows
- `tests/integration/workflows/test_ratchet_workflows.py` - Complete ratchet scenarios
- `tests/integration/workflows/test_manifest_generation.py` - Full manifest creation flows

### 2.3 Property-Based Tests Migration

Move all Hypothesis tests to `tests/property_based/`:

- `test_prop_manifest.py` → `tests/property_based/test_manifest.py`
- `test_prop_paths.py` → `tests/property_based/test_paths.py`
- `test_prop_readiness.py` → `tests/property_based/test_readiness.py`
- Extract property tests from `test_model_type_enums.py` → `tests/property_based/test_enums.py`

Create `tests/property_based/strategies/common.py` for shared Hypothesis strategies.

### 2.4 Performance Tests Migration

Move performance tests:

- `tests/perf/test_benchmarks.py` → `tests/performance/benchmarks/test_core_operations.py`

---

## Phase 3: Extract Shared Components

### 3.1 Create Centralized Test Fixtures Module

**Location**: `tests/fixtures/`

**Extract from conftest.py**:

Create `tests/fixtures/builders.py`:

- Move `sample_summary` fixture → `build_sample_summary()` function
- Move `_build_readiness_entries()` helpers
- Move `_build_sample_run()` helpers
- Create `TestDataBuilder` class for reusable test data

Create `tests/fixtures/stubs.py`:

- Move `StubEngine` and other mock classes
- Create reusable stub factories

Create `tests/fixtures/snapshots.py`:

- Move snapshot-related fixtures
- Create snapshot assertion helpers

### 3.2 Refactor conftest.py Files

**Global conftest.py** (`tests/conftest.py`):

- Keep only truly global fixtures
- Import from fixtures module
- Define pytest configuration (markers, plugins)

**Domain-specific conftest.py files**:

- `tests/unit/cli/conftest.py` - CLI-specific fixtures
- `tests/unit/engines/conftest.py` - Engine stub fixtures
- `tests/integration/conftest.py` - Integration test fixtures
- `tests/property_based/conftest.py` - Hypothesis settings

---

## Phase 4: Implement Test Markers & Configuration

### 4.1 Define Pytest Markers

Add to `tests/conftest.py`:

```python
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower, multiple components)")
    config.addinivalue_line("markers", "property: Property-based tests")
    config.addinivalue_line("markers", "benchmark: Performance benchmark tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "cli: CLI-related tests")
    config.addinivalue_line("markers", "engine: Engine-related tests")
    config.addinivalue_line("markers", "ratchet: Ratchet feature tests")
```

### 4.2 Update pytest Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
minversion = "8.4"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-ra",                    # Show summary of all test outcomes
    "--strict-markers",       # Enforce marker registration
    "--strict-config",        # Enforce configuration validation
    "-v",                     # Verbose output
]

# Test discovery patterns
filterwarnings = [
    "error",                  # Treat warnings as errors
    "ignore::DeprecationWarning",
]
```

---

## Phase 5: Improve Test Quality

### 5.1 Add Test Documentation

Create comprehensive `tests/README.md` with:

- Test structure overview
- Running different test categories
- Writing test guidelines
- Fixture usage
- Coverage requirements
- CI/CD integration

### 5.2 Standardize Test Patterns

Enforce consistent patterns:

- Use AAA (Arrange-Act-Assert) pattern
- One assertion per test (where reasonable)
- Descriptive test names: `test_<what>_<condition>_<expected_result>`
- Use parametrize for similar tests with different inputs
- Avoid test interdependencies

### 5.3 Extract Test Utilities

Create helper modules:

- `tests/fixtures/assertions.py` - Custom assertion helpers
- `tests/fixtures/matchers.py` - Custom matchers for complex objects
- `tests/fixtures/factories.py` - Factory functions for test data

---

## Phase 6: CI/CD Integration

### 6.1 Update CI Pipeline

Update `.github/workflows/ci.yml` to support:

- Separate test stages by type
- Parallel execution where possible
- Coverage tracking per test type

Suggested workflow stages:

```yaml
test:unit:
  script: pytest tests/unit -m unit --cov=typewiz

test:integration:
  script: pytest tests/integration -m integration

test:property:
  script: pytest tests/property_based -m property --hypothesis-profile=ci

test:performance:
  script: pytest tests/performance -m benchmark --benchmark-only
```

### 6.2 Coverage Requirements

- Overall coverage: 95%+ (as per AGENTS.md)
- Per-module minimum: 80%
- Add coverage ratcheting to prevent regression

---

## Phase 7: Migration Execution Steps

### Step-by-Step Migration Checklist

1. ✅ **Create new directory structure** (no code changes yet)
2. ✅ **Create fixtures module** and extract shared code
3. ✅ **Move property-based tests** (smallest category, easiest to migrate)
4. ✅ **Move performance tests** (already isolated)
5. ✅ **Categorize and move unit tests** (by domain, one at a time)
6. ✅ **Extract and move integration tests** (requires refactoring test_cli.py)
7. ✅ **Update all conftest.py files**
8. ✅ **Add markers to all tests**
9. ✅ **Update CI/CD configuration**
10. ✅ **Update documentation**
11. ✅ **Verify all tests pass** in new structure
12. ✅ **Run mypy, pyright, ruff** (as per AGENTS.md)
13. ✅ **Remove old test files**
14. ✅ **Git commit** (after all checks pass)

---

## Success Criteria

### Organization

- ✅ Tests organized by type (unit/integration/property/performance)
- ✅ Unit tests further organized by domain
- ✅ No test file > 500 lines
- ✅ Shared fixtures extracted to reusable modules

### Discoverability

- ✅ Clear naming conventions
- ✅ Comprehensive test markers
- ✅ Documentation for each test category

### Performance

- ✅ Unit tests run in < 30 seconds
- ✅ Full test suite runs in < 5 minutes
- ✅ Can run test subsets independently

### Maintainability

- ✅ No code duplication in test setup
- ✅ Clear test data builders
- ✅ Domain-specific fixtures isolated
- ✅ Easy to add new tests

### Quality (per AGENTS.md)

- ✅ 95%+ code coverage maintained
- ✅ All tests passing
- ✅ mypy strict mode passing
- ✅ pyright strict mode passing
- ✅ Ruff linting passing
- ✅ No flaky tests
- ✅ Clear test failure messages

---

## Quick Wins (High Impact, Low Effort)

1. **Create directory structure** - 15 minutes
2. **Add pytest markers** - 30 minutes
3. **Extract fixtures/builders.py** - 1 hour
4. **Move property-based tests** - 30 minutes
5. **Move performance tests** - 15 minutes
6. **Create tests/README.md** - 30 minutes

**Total Quick Wins: ~3 hours of work for major improvements**

---

## Benefits

### Developer Experience

- Faster test discovery and navigation
- Easier to run relevant test subsets
- Clear separation of fast vs slow tests
- Better IDE integration

### Code Quality

- Better test isolation
- Reduced code duplication
- Improved maintainability
- Clearer test purpose

### CI/CD

- Parallel test execution by type
- Faster feedback loops
- Better failure diagnostics
- Optimized resource usage

### Scalability

- Easy to add new tests in the right location
- Clear patterns for new contributors
- Sustainable growth as codebase expands
- Reduced cognitive load

---

## References

This plan follows industry standards from:

- Google Testing Blog
- Microsoft Engineering Best Practices
- Python community's test organization patterns
- pytest best practices documentation
- Test Pyramid principles (many unit tests, fewer integration tests, minimal E2E)

---

## Notes for AI Agents

When executing this plan via codex CLI:

1. Always activate `.venv` before running commands (per AGENTS.md)
2. Use `make` targets where available
3. After each phase, run `make ci.check` to ensure all gates pass
4. Move files using `git mv` to preserve history
5. After all changes, run: `mypy`, `pyright`, `ruff`, and `pytest` before committing
6. Only commit when all checks pass (per AGENTS.md line 99)
7. Provide detailed multi-line commit messages summarizing all changes
