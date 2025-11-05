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
  TYPEWIZ ?= $(BIN_DIR)/typewiz.exe
else
  BIN_DIR := $(VENV)/bin
  PYTHON ?= $(BIN_DIR)/python
  PIP ?= $(BIN_DIR)/pip
  RUFF ?= $(BIN_DIR)/ruff
  MYPY ?= $(BIN_DIR)/mypy
  PYRIGHT ?= $(BIN_DIR)/pyright
  PYTEST ?= $(BIN_DIR)/pytest
  TYPEWIZ ?= $(BIN_DIR)/typewiz
endif

# Reports / defaults
REPORTS_DIR ?= reports
TYPING_REPORT_DIR ?= $(REPORTS_DIR)/typing
MANIFEST_PATH ?= $(TYPING_REPORT_DIR)/typing_audit.json
TYPEWIZ_STATUSES ?= blocked ready
TYPEWIZ_LEVEL ?= folder
TYPEWIZ_LIMIT ?= 20

.PHONY: \
  help %.help \
  ci.precommit.install ci.check \
  all.test all.lint all.type all.format all.fix \
  lint lint.ruff lint.format format fix \
  type type.mypy type.pyright type.verify typing.run typing.baseline typing.strict typing.ci \
  pytest.all pytest.verbose pytest.failfast pytest.cov pytest.clean \
  tests.all tests.verbose tests.failfast tests.cov tests.clean \
  sec.lint sec.bandit \
  bench \
  verifytypes \
  hooks.update \
  check.error-codes \
  precommit.check \
  typewiz.audit typewiz.dashboard typewiz.readiness typewiz.clean \
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
lint: lint.ruff lint.format ## Lint + format checks

lint.ruff: ## Run ruff lint
	$(RUFF) check

lint.format: ## Run ruff format check (no changes)
	$(RUFF) format --check

format: ## Apply ruff formatter
	$(RUFF) format

fix: ## Apply ruff formatter and autofix lints
	$(RUFF) format
	$(RUFF) check --fix

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
	$(MYPY)

type.pyright: ## Run pyright using repo config
	$(PYRIGHT) -p pyrightconfig.json

type.verify: ## Verify public typing completeness via pyright
	PYTHONPATH=src $(PYRIGHT) --verifytypes typewiz --ignoreexternal

verifytypes: ## Alias for type.verify (pyright --verifytypes)
	@$(MAKE) type.verify

typing.run: typing.baseline typing.strict ## Run baseline then strict checks

typing.baseline: ## Run pyright then mypy checks
	$(PYRIGHT) -p pyrightconfig.json
	$(MYPY)

typing.strict: ## Enforce strict gates (ruff + mypy strict again)
	$(RUFF) check
	$(MYPY)

typing.ci: ## Generate Typewiz outputs (JSON/MD/HTML) for CI insight
	mkdir -p $(TYPING_REPORT_DIR)
	$(TYPEWIZ) audit --max-depth 3 --mode full --manifest $(MANIFEST_PATH) --readiness --readiness-status blocked --readiness-status ready || true
	$(TYPEWIZ) dashboard --manifest $(MANIFEST_PATH) --format json --output $(TYPING_REPORT_DIR)/dashboard.json || true
	$(TYPEWIZ) dashboard --manifest $(MANIFEST_PATH) --format markdown --output $(TYPING_REPORT_DIR)/dashboard.md || true
	$(TYPEWIZ) dashboard --manifest $(MANIFEST_PATH) --format html --output $(TYPING_REPORT_DIR)/dashboard.html || true

##@ Tests
pytest.all: ## Run pytest quietly
	$(PYTEST) -q

pytest.verbose: ## Run pytest verbosely
	$(PYTEST) -v

pytest.failfast: ## Run pytest, stopping on first failure
	$(PYTEST) -x

pytest.cov: ## Run pytest with coverage on src/typewiz (90% gate)
	$(PYTEST) --cov=src/typewiz --cov-report=term --cov-fail-under=90

pytest.clean: ## Clean pytest cache
	rm -rf .pytest_cache

##@ Typewiz
typewiz.audit: ## Generate Typewiz audit manifest
	mkdir -p $(TYPING_REPORT_DIR)
	$(TYPEWIZ) audit --max-depth 3 --manifest $(MANIFEST_PATH) --readiness --readiness-status blocked --readiness-status ready

typewiz.dashboard: ## Render Typewiz dashboards (MD + HTML)
	@$(MAKE) typewiz.audit
	$(TYPEWIZ) dashboard --manifest $(MANIFEST_PATH) --format markdown --output $(TYPING_REPORT_DIR)/dashboard.md
	$(TYPEWIZ) dashboard --manifest $(MANIFEST_PATH) --format html --output $(TYPING_REPORT_DIR)/dashboard.html

typewiz.readiness: ## Show Typewiz readiness summary
	@$(MAKE) typewiz.audit
	$(TYPEWIZ) readiness --manifest $(MANIFEST_PATH) --level $(TYPEWIZ_LEVEL) $(foreach status,$(TYPEWIZ_STATUSES),--status $(status)) --limit $(TYPEWIZ_LIMIT) || true

typewiz.clean: ## Remove Typewiz caches and reports
	rm -rf .typewiz_cache
	rm -rf $(TYPING_REPORT_DIR)

##@ Internal checks
check.error-codes: ## Verify error code registry and documentation are in sync
	$(PYTHON) scripts/check_error_codes.py

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

clean.all: typewiz.clean pytest.clean clean.mypy clean.pyright clean.coverage clean.pycache ## Remove all local caches


.DEFAULT_GOAL := help
HELP_GROUP_FORMAT := "\n\033[1m%s\033[0m\n"
HELP_CMD_FORMAT := "  \033[36m%-32s\033[0m %s\n"

help:
	@printf $(HELP_GROUP_FORMAT) "Typewiz Makefile Commands"
	@printf $(HELP_GROUP_FORMAT) "Usage:"
	@printf "  \033[36m%s\033[0m%s\033[36m%-26s\033[0m%s\n" "make " "or" " make help" " View this help message"
	@awk 'BEGIN {FS=":.*##"} \
		/^##@/ { printf $(HELP_GROUP_FORMAT), substr($$0,5); next } \
		/^[a-zA-Z0-9_.-•]+:.*##/ { printf $(HELP_CMD_FORMAT), $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@printf "\n"
	@printf $(HELP_GROUP_FORMAT) "Common arguments (override per call):"
	@printf $(HELP_CMD_FORMAT) "TYPEWIZ_LEVEL=folder|file" " Scope readiness view"
	@printf $(HELP_CMD_FORMAT) "TYPEWIZ_STATUSES=blocked\ ready" " Filter readiness statuses"
	@printf $(HELP_CMD_FORMAT) "TYPEWIZ_LIMIT=20" " Limit entries in readiness view"
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

##@ Benchmarks
bench: ## Run performance benchmarks (requires pytest-benchmark plugin)
	$(PYTEST) tests/perf/test_benchmarks.py --benchmark-only

##@ Hooks
hooks.update: ## Update pre-commit hooks to latest versions
	$(PIP) install --quiet pre-commit || true
	pre-commit autoupdate

tests.cov: ## Alias for pytest.cov
	@$(MAKE) pytest.cov

tests.clean: ## Alias for pytest.clean
	@$(MAKE) pytest.clean
##@ Security
sec.lint: ## Advisory security lint (ruff S-rules)
	$(RUFF) check --select S

sec.bandit: ## Run Bandit if available (advisory)
	@if command -v bandit >/dev/null 2>&1; then \
	  bandit -q -r src -x src/typewiz/logging_utils.py; \
	else \
	  echo "[advisory] bandit not installed; skipping"; \
	fi
