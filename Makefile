MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# Tooling
VENV ?= .venv

ifeq ($(origin OS), undefined)
  OS_NAME := $(shell uname -s 2>/dev/null)
else
  OS_NAME := $(OS)
endif

ifeq ($(OS_NAME),Windows_NT)
  BIN_DIR := $(VENV)/Scripts
  PYTHON ?= $(BIN_DIR)/python.exe
  PIP ?= $(BIN_DIR)/pip.exe
  RUFF ?= $(BIN_DIR)/ruff.exe
  MYPY ?= $(BIN_DIR)/mypy.exe
  PYRIGHT ?= $(BIN_DIR)/pyright.exe
  PYTEST ?= $(BIN_DIR)/pytest.exe
  RATCHETR ?= $(BIN_DIR)/ratchetr.exe
else
  BIN_DIR := $(VENV)/bin
  PYTHON ?= $(BIN_DIR)/python
  PIP ?= $(BIN_DIR)/pip
  RUFF ?= $(BIN_DIR)/ruff
  MYPY ?= $(BIN_DIR)/mypy
  PYRIGHT ?= $(BIN_DIR)/pyright
  PYTEST ?= $(BIN_DIR)/pytest
  RATCHETR ?= $(BIN_DIR)/ratchetr
endif

# Reports / defaults
REPORTS_DIR ?= reports
TYPING_REPORT_DIR ?= $(REPORTS_DIR)/typing
MANIFEST_PATH ?= $(TYPING_REPORT_DIR)/typing_audit.json
RATCHETR_STATUSES ?= blocked ready
RATCHETR_LEVEL ?= folder
RATCHETR_LIMIT ?= 20
# NOTE: pyright --verifytypes only works when the package has been pip-installed (requires network).
# Sandbox environments cannot perform that install today, so keep the gate opt-in.
VERIFYTYPES_ENABLED ?= 0
VERIFYTYPES_PACKAGE ?= ratchetr

.PHONY: \
  help %.help \
  ci.precommit.install ci.check \
  all.test all.lint all.type all.format all.fix \
  lint lint.ruff lint.format lint.pylint format fix \
  type type.mypy type.pyright type.verify typing.run typing.baseline typing.strict typing.ci \
  pytest.all pytest.verbose pytest.failfast pytest.unit pytest.integration pytest.property pytest.performance pytest.cov pytest.clean \
  tests.all tests.verbose tests.failfast tests.unit tests.integration tests.property tests.performance tests.cov tests.clean \
  sec.lint sec.bandit sec.safety sec.all \
  bench \
  verifytypes \
  hooks.update \
  package.build package.check package.clean package.install-test \
  check.error-codes \
  precommit.check \
  ratchetr.audit ratchetr.dashboard ratchetr.readiness ratchetr.clean \
  clean.all clean.mypy clean.pyright clean.pycache clean.coverage

##@ CI
ci.precommit.install: ## Install pre-commit and register hooks
	$(PIP) install --quiet pre-commit || true
	pre-commit install

ci.check: typing.run all.lint all.type pytest.cov ## Run typing, lint, and tests with coverage gate (CI parity)

##@ Aggregate
all.test: ## Run full pytest suite quietly
	$(PYTEST) -q

all.lint: ## Run ruff lint + formatter check
	@$(MAKE) lint

all.type: ## Run mypy + pyright
	@$(MAKE) type

all.format: ## Apply ruff formatting to the codebase
	@$(MAKE) format

all.fix: ## Apply ruff formatting and autofix lints
	@$(MAKE) fix

##@ Lint & Format
lint: lint.ruff lint.format lint.markdown ## Lint + format checks

lint.ruff: ## Run ruff lint
	uv run $(RUFF) check

lint.format: ## Run ruff format check (no changes)
	uv run $(RUFF) format --check

lint.markdown: ## Run markdownlint on all markdown files
	uv run markdownlint '**/*.md' --ignore node_modules --ignore .venv --ignore dist --ignore build --ignore 'docs/archive/**' --ignore 'docs/release_docs_plan.md'

format: ## Apply ruff formatter
	uv run $(RUFF) format

fix: ## Apply ruff formatter and autofix lints
	uv run $(RUFF) format
	uv run $(RUFF) check --fix

##@ Pre-commit
precommit.check: ## Run lint (ruff) and typing checks in parallel (used by pre-commit)
	@set -euo pipefail; \
	 $(MAKE) lint.ruff & \
	 lint_pid=$$!; \
	 $(MAKE) type.mypy & \
	 mypy_pid=$$!; \
	 $(MAKE) type.pyright & \
	 pyright_pid=$$!; \
	 wait $$lint_pid; \
	 wait $$mypy_pid; \
	 wait $$pyright_pid

##@ Typing
type: type.mypy type.pyright ## Run mypy + pyright

type.mypy: ## Run mypy (strict)
	uv run $(MYPY) --no-incremental

type.pyright: ## Run pyright using repo config from pyproject.toml
	uv run $(PYRIGHT)

type.verify: ## Verify public typing completeness via pyright (opt-in via VERIFYTYPES_ENABLED=1)
ifeq ($(VERIFYTYPES_ENABLED),1)
	PYTHONPATH=src uv run $(PYRIGHT) --verifytypes $(VERIFYTYPES_PACKAGE) --ignoreexternal
else
	@echo "[skip] uv run pyright --verifytypes requires $(VERIFYTYPES_PACKAGE) to be pip-installed; set VERIFYTYPES_ENABLED=1 after installing it."
endif

verifytypes: ## Alias for type.verify (pyright --verifytypes)
	@$(MAKE) type.verify

typing.run: typing.baseline typing.strict type.verify ## Run baseline then strict checks plus public typing

typing.baseline: ## Run pyright then mypy checks
	uv run $(PYRIGHT)
	uv run $(MYPY) --no-incremental
	uv run $(MYPY) --no-incremental

typing.strict: ## Enforce strict gates (ruff + mypy strict again)
	uv run $(RUFF) check
	uv run $(MYPY) --no-incremental

typing.ci: ## Generate Ratchetr outputs (JSON/MD/HTML) for CI insight
	mkdir -p $(TYPING_REPORT_DIR)
	uv run $(RATCHETR) audit --max-depth 3 --mode full --manifest $(MANIFEST_PATH) --readiness --readiness-status blocked --readiness-status ready || true
	uv run $(RATCHETR) dashboard --manifest $(MANIFEST_PATH) --format json --output $(TYPING_REPORT_DIR)/dashboard.json || true
	uv run $(RATCHETR) dashboard --manifest $(MANIFEST_PATH) --format markdown --output $(TYPING_REPORT_DIR)/dashboard.md || true
	uv run $(RATCHETR) dashboard --manifest $(MANIFEST_PATH) --format html --output $(TYPING_REPORT_DIR)/dashboard.html || true

##@ Tests
pytest.all: ## Run pytest quietly
	uv run $(PYTEST) -q

pytest.verbose: ## Run pytest verbosely
	uv run $(PYTEST) -v

pytest.failfast: ## Run pytest, stopping on first failure
	uv run $(PYTEST) -x

pytest.unit: ## Run only unit suites (tests/unit)
	uv run $(PYTEST) -q tests/unit

pytest.integration: ## Run only integration suites (tests/integration)
	uv run $(PYTEST) -q tests/integration

pytest.property: ## Run only property-based suites (tests/property_based)
	uv run $(PYTEST) -q tests/property_based

pytest.performance: ## Run only performance suites (tests/performance)
	uv run $(PYTEST) -q tests/performance

pytest.cov: ## Run pytest with coverage on src/ratchetr (95% gate)
	uv run $(PYTEST) --cov=src/ratchetr --cov-report=term --cov-fail-under=95

pytest.clean: ## Clean pytest cache
	rm -rf .pytest_cache

##@ Ratchetr
ratchetr.audit: ## Generate Ratchetr audit manifest
	mkdir -p $(TYPING_REPORT_DIR)
	uv run $(RATCHETR) audit --max-depth 3 --manifest $(MANIFEST_PATH) --readiness --readiness-status blocked --readiness-status ready

ratchetr.dashboard: ## Render Ratchetr dashboards (MD + HTML)
	@$(MAKE) ratchetr.audit
	uv run $(RATCHETR) dashboard --manifest $(MANIFEST_PATH) --format markdown --output $(TYPING_REPORT_DIR)/dashboard.md
	uv run $(RATCHETR) dashboard --manifest $(MANIFEST_PATH) --format html --output $(TYPING_REPORT_DIR)/dashboard.html

ratchetr.readiness: ## Show Ratchetr readiness summary
	@$(MAKE) ratchetr.audit
	uv run $(RATCHETR) readiness --manifest $(MANIFEST_PATH) --level $(RATCHETR_LEVEL) $(foreach status,$(RATCHETR_STATUSES),--status $(status)) --limit $(RATCHETR_LIMIT) || true

ratchetr.clean: ## Remove Ratchetr caches and reports
	rm -rf .ratchetr_cache
	rm -rf $(TYPING_REPORT_DIR)

##@ Internal checks
check.error-codes: ## Verify error code registry and documentation are in sync
	uv run $(PYTHON) scripts/check_error_codes.py

##@ Cleaning
clean.mypy: ## Remove mypy cache directory
	rm -rf .mypy_cache

clean.pyright: ## Remove Pyright cache directory
	rm -rf .pyrightcache

clean.pycache: ## Remove Python bytecode and __pycache__ dirs across repo
	find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.py[co]' \) -delete
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

clean.coverage: ## Remove coverage artifacts
	rm -f .coverage
	rm -rf htmlcov

clean.all: ratchetr.clean pytest.clean clean.mypy clean.pyright clean.coverage clean.pycache ## Remove all local caches


.DEFAULT_GOAL := help
HELP_GROUP_FORMAT := "\n\033[1m%s\033[0m\n"
HELP_CMD_FORMAT := "  \033[36m%-32s\033[0m %s\n"

help:
	@printf $(HELP_GROUP_FORMAT) "Ratchetr Makefile Commands"
	@printf $(HELP_GROUP_FORMAT) "Usage:"
	@printf "  \033[36m%s\033[0m%s\033[36m%-26s\033[0m%s\n" "make " "or" " make help" " View this help message"
	@awk 'BEGIN {FS=":.*##"} \
		/^##@/ { printf $(HELP_GROUP_FORMAT), substr($$0,5); next } \
		/^[a-zA-Z0-9_.-•]+:.*##/ { printf $(HELP_CMD_FORMAT), $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@printf "\n"
	@printf $(HELP_GROUP_FORMAT) "Common arguments (override per call):"
	@printf $(HELP_CMD_FORMAT) "RATCHETR_LEVEL=folder|file" " Scope readiness view"
	@printf $(HELP_CMD_FORMAT) "RATCHETR_STATUSES=blocked\ ready" " Filter readiness statuses"
	@printf $(HELP_CMD_FORMAT) "RATCHETR_LIMIT=20" " Limit entries in readiness view"
	@printf "\nHint: run \033[36mmake <group>.help\033[0m for a specific group (e.g., 'tests.help', 'lint.help', 'type.help').\n"

%.help:
	@awk 'BEGIN {FS=":.*##"} \
		/^[a-zA-Z0-9_.-•]+:.*##/ { printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep "^  .*$(firstword $(MAKECMDGOALS))\..*" || true

##@ Tests (aliases)
tests.all: ## Alias for pytest.all
	@$(MAKE) pytest.all

tests.verbose: ## Alias for pytest.verbose
	@$(MAKE) pytest.verbose

tests.failfast: ## Alias for pytest.failfast
	@$(MAKE) pytest.failfast

tests.unit: ## Alias for pytest.unit
	@$(MAKE) pytest.unit

tests.integration: ## Alias for pytest.integration
	@$(MAKE) pytest.integration

tests.property: ## Alias for pytest.property
	@$(MAKE) pytest.property

tests.performance: ## Alias for pytest.performance
	@$(MAKE) pytest.performance

##@ Benchmarks
bench: ## Run performance benchmarks (requires pytest-benchmark plugin)
	uv run $(PYTEST) tests/performance/benchmarks --benchmark-only

##@ Hooks
hooks.update: ## Update pre-commit hooks to latest versions
	uv $(PIP) install --quiet pre-commit || true
	uv run pre-commit autoupdate

##@ Packaging
package.build: ## Build sdist and wheel into dist/
	uv run $(PYTHON) -m build --no-isolation

package.check: package.build ## Run Twine check on built artifacts
	uv run $(PYTHON) -m twine check dist/*


package.install-test: package.build ## Install built wheel in a temporary venv to ensure installability
	uv run $(PYTHON) scripts/install_test_wheel.py


package.clean: ## Remove build artifacts
	uv run $(PYTHON) scripts/clean_build_artifacts.py

tests.cov: ## Alias for pytest.cov
	@$(MAKE) pytest.cov

tests.clean: ## Alias for pytest.clean
	@$(MAKE) pytest.clean
##@ Security
sec.lint: ## Advisory security lint (ruff S-rules)
	uv run $(RUFF) check --select S

sec.bandit: ## Run Bandit security scanner
	@mkdir -p out/security
	uv run $(BIN_DIR)/bandit -c pyproject.toml -r src/ -f json -o out/security/bandit-report.json || true
	@echo "Bandit report: out/security/bandit-report.json"

sec.safety: ## Run Safety dependency vulnerability scanner
	@mkdir -p out/security
	uv run $(BIN_DIR)/safety scan --json > out/security/safety-report.json || true
	@echo "Safety report: out/security/safety-report.json"

sec.all: sec.lint sec.bandit sec.safety ## Run all security checks

##@ Code Quality
lint.pylint: ## Run Pylint code quality checks
	@mkdir -p out/lint
	uv run $(BIN_DIR)/pylint --output-format=json --reports=n src/ > out/lint/pylint.json || true
	@echo "Pylint report: out/lint/pylint.json"
