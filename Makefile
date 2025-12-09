MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c


# ----------------------------------------------------------------------
# Core tool wiring
# ----------------------------------------------------------------------

UV := uv run

OUTPUT_DIR         ?= out
TYPING_REPORT_DIR  ?= $(OUTPUT_DIR)/ratchetr
MANIFEST_PATH      ?= $(TYPING_REPORT_DIR)/typing_audit.json

RATCHETR_STATUSES  ?= blocked ready
RATCHETR_LEVEL     ?= folder
RATCHETR_LIMIT     ?= 20
# Extra flags forwarded directly to `ratchetr audit` (e.g., --root src/ratchetr)
RATCHETR_FLAGS     ?=

VERIFYTYPES_DISABLED ?= 0
VERIFYTYPES_PACKAGE  ?= ratchetr

.DEFAULT_GOAL := help

.PHONY: \
  all all.full all.test all.lint all.type all.format all.fix all.sec all.ratchetr \
  lint lint.ruff lint.ruff.fix lint.format lint.format.fix lint.markdown lint.pylint lint.fix \
  type type.mypy type.pyright type.verify type.clean \
  test test.verbose test.failfast test.unit test.integration test.property test.performance test.cov test.bench \
  test.clean test.clean.pytest test.clean.coverage test.clean.hypothesis test.clean.benchmarks \
  ratchetr ratchetr.audit ratchetr.dashboard ratchetr.dashboard.json ratchetr.readiness ratchetr.clean ratchetr.all \
  sec sec.lint sec.bandit sec.safety \
  package.build package.check package.install-test package.clean \
  check.error-codes \
  clean clean.pycache clean.cache clean.caches clean.mypy clean.pyright clean.type clean.ruff clean.pylint clean.lint \
  clean.coverage clean.pytest clean.hypothesis clean.benchmarks clean.test \
  clean.bandit clean.safety clean.sec clean.package clean.ratchetr clean.full \
  ci.check ci.package ci.all \
  precommit.check precommit.update precommit.install \
  help


# ----------------------------------------------------------------------
##@ Aggregate
# ----------------------------------------------------------------------

all.test: test ## Run full test suite
all.lint: lint ## Run all lint checks (ruff, pylint, markdown)
all.type: type ## Run mypy + pyright (+ verify-types unless VERIFYTYPES_DISABLED=1)
all.format: lint.format ## Check formatting (no changes)
all.fix: lint.fix ## Apply formatter and autofix lints
all.sec: sec ## Run all security checks
all.ratchetr: ratchetr.all ## Run full Ratchetr report generation
all: all.lint all.type test.cov all.sec ## Run lint, typing, tests (w/coverage), and security
all.full: all.fix all all.ratchetr ## Run all checks, fixes, and report generation


# ----------------------------------------------------------------------
##@ Lint & Format
# ----------------------------------------------------------------------

lint: lint.ruff lint.format lint.pylint lint.markdown ## Lint code and docs 

lint.ruff: ## Run ruff lint
	$(UV) ruff check

lint.ruff.fix: ## Apply ruff formatter
	$(UV) ruff check --fix

lint.format: ## Check ruff formatting (no changes)
	$(UV) ruff format --check

lint.format.fix: ## Apply ruff formatter
	$(UV) ruff format

lint.markdown: ## Run pymarkdownlnt on markdown files
	$(UV) pymarkdownlnt scan .

lint.pylint: ## Run Pylint code quality checks
	@mkdir -p $(OUTPUT_DIR)/lint
	$(UV) pylint src/ratchetr --output-format=json --reports=n > $(OUTPUT_DIR)/lint/pylint.json || true
	@echo "Pylint report: $(OUTPUT_DIR)/lint/pylint.json"

lint.fix: lint.ruff.fix lint.format.fix ## Apply formatter and autofix lints


# ----------------------------------------------------------------------
##@ Typing
# ----------------------------------------------------------------------

type: type.mypy type.pyright type.verify ## Run mypy + pyright (+ verify-types unless VERIFYTYPES_DISABLED=1)

type.mypy: ## Run mypy
	$(UV) mypy

type.pyright: ## Run pyright
	$(UV) pyright

type.verify: ## Verify public typing completeness via pyright (opt-out via VERIFYTYPES_DISABLED=1)
ifeq ($(VERIFYTYPES_DISABLED),0)
	PYTHONPATH=src $(UV) pyright --verifytypes $(VERIFYTYPES_PACKAGE) --ignoreexternal
else
	@echo "[skip] pyright --verifytypes disabled via VERIFYTYPES_DISABLED=1 (package: $(VERIFYTYPES_PACKAGE))"
endif

type.clean: clean.type ## Clean all typing caches


# ----------------------------------------------------------------------
##@ Tests
# ----------------------------------------------------------------------

test: ## Run pytest (quiet)
	$(UV) pytest -q

test.verbose: ## Run pytest verbosely
	$(UV) pytest -v

test.failfast: ## Run pytest, stopping on first failure
	$(UV) pytest -x

test.unit: ## Run unit tests (tests/unit)
	$(UV) pytest -q tests/unit

test.integration: ## Run integration tests (tests/integration)
	$(UV) pytest -q tests/integration

test.property: ## Run property-based tests (tests/property_based)
	$(UV) pytest -q tests/property_based

test.performance: ## Run performance tests (tests/performance)
	$(UV) pytest -q tests/performance

test.cov: ## Run pytest with coverage (95% gate) on src/ratchetr
	$(UV) pytest --cov=src/ratchetr --cov-report=term --cov-fail-under=95

test.bench: ## Run performance benchmarks (requires pytest-benchmark plugin)
	$(UV) pytest tests/performance/benchmarks --benchmark-only

test.clean.pytest: clean.pytest ## Clean pytest cache
test.clean.coverage: clean.coverage ## Clean coverage artifacts
test.clean.hypothesis: clean.hypothesis ## Clean Hypothesis cache
test.clean.benchmarks: clean.benchmarks ## Clean pytest-benchmark cache
test.clean: clean.test ## Clean all test caches and artifacts


# ----------------------------------------------------------------------
##@ Ratchetr
# ----------------------------------------------------------------------

$(MANIFEST_PATH):  ## Generate Ratchetr audit manifest
	mkdir -p $(TYPING_REPORT_DIR)
	$(UV) ratchetr audit \
		--manifest $(MANIFEST_PATH) \
		$(RATCHETR_FLAGS)
		--readiness \
		$(foreach status,$(RATCHETR_STATUSES),--readiness-status $(status)) \

ratchetr: ratchetr.audit ratchetr.dashboard ratchetr.readiness ## Run all Ratchetr typing report generation steps

ratchetr.audit: $(MANIFEST_PATH) ## Logical alias
	@:

ratchetr.dashboard: $(MANIFEST_PATH) ## Render Ratchetr dashboards (Markdown + HTML)
	$(UV) ratchetr dashboard --manifest $(MANIFEST_PATH) --format markdown --output $(TYPING_REPORT_DIR)/dashboard.md
	$(UV) ratchetr dashboard --manifest $(MANIFEST_PATH) --format html     --output $(TYPING_REPORT_DIR)/dashboard.html

ratchetr.dashboard.json: $(MANIFEST_PATH) ## Render Ratchetr dashboard in JSON format
	$(UV) ratchetr dashboard --manifest $(MANIFEST_PATH) --format json     --output $(TYPING_REPORT_DIR)/dashboard.json

ratchetr.readiness: $(MANIFEST_PATH) ## Show Ratchetr readiness summary
	$(UV) ratchetr readiness \
		--manifest $(MANIFEST_PATH) \
		--level $(RATCHETR_LEVEL) \
		$(foreach status,$(RATCHETR_STATUSES),--status $(status)) \
		--limit $(RATCHETR_LIMIT) || true

ratchetr.all: ratchetr ratchetr.dashboard.json ## Include json report format with full run

ratchetr.clean: clean.ratchetr ## Remove Ratchetr caches and reports


# ----------------------------------------------------------------------
##@ Security
# ----------------------------------------------------------------------

sec: sec.lint sec.bandit sec.safety ## Run all security checks

sec.lint: ## Security lint via ruff S-rules
	$(UV) ruff check --select S

sec.bandit: ## Run Bandit security scanner
	mkdir -p $(OUTPUT_DIR)/security
	$(UV) bandit -c pyproject.toml -r src/ -f json -o $(OUTPUT_DIR)/security/bandit-report.json || true
	@echo "Bandit report: $(OUTPUT_DIR)/security/bandit-report.json"

sec.safety: ## Run Safety dependency scanner
	mkdir -p $(OUTPUT_DIR)/security
	$(UV) safety scan --json > $(OUTPUT_DIR)/security/safety-report.json || true
	@echo "Safety report: $(OUTPUT_DIR)/security/safety-report.json"


# ----------------------------------------------------------------------
##@ Packaging
# ----------------------------------------------------------------------

package.build: ## Build sdist and wheel into dist/
	$(UV) python -m build --no-isolation

package.check: ## Run Twine check on built artifacts
	$(UV) twine check dist/*

package.install-test: ## Install built wheel in a temporary venv to ensure installability
	$(UV) python scripts/install_test_wheel.py

package.clean: ## Remove build artifacts
	$(UV) python scripts/clean_build_artifacts.py


# ----------------------------------------------------------------------
##@ Internal checks
# ----------------------------------------------------------------------

check.error-codes: ## Verify error code registry and documentation are in sync
	$(UV) python scripts/check_error_codes.py


# ----------------------------------------------------------------------
##@ Cleaning
# ----------------------------------------------------------------------

clean.mypy: ## Remove mypy cache
	rm -rf .mypy_cache

clean.pyright: ## Remove pyright cache
	rm -rf .pyrightcache

clean.type: clean.mypy clean.pyright ## Remove typing caches

clean.ruff: ## Remove ruff cache
	rm -rf .ruff_cache

clean.pylint: ## Remove pylint cache
	rm -rf .pylint.d
	rm -f $(OUTPUT_DIR)/lint/pylint.json

clean.lint: clean.ruff clean.pylint ## Remove lint caches

clean.pycache: ## Remove Python bytecode and __pycache__ dirs
	find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.py[co]' \) -delete
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

clean.cache: ## Remove .cache directories
	find . -type d -name .cache -prune -exec rm -rf {} +

clean.caches: clean.pycache clean.cache ## Remove all common caches

clean.coverage: ## Remove coverage artifacts
	rm -f .coverage
	rm -rf htmlcov

clean.pytest: ## Clean test caches
	rm -rf .pytest_cache

clean.hypothesis: ## Remove Hypothesis caches
	rm -rf .hypothesis

clean.benchmarks: ## Remove pytest-benchmark caches
	rm -rf .benchmarks

clean.test: clean.pytest clean.coverage clean.hypothesis clean.benchmarks ## Remove test caches and coverage artifacts

clean.bandit: ## Remove Bandit report
	rm -f $(OUTPUT_DIR)/security/bandit-report.json

clean.safety: ## Remove Safety report
	rm -f $(OUTPUT_DIR)/security/safety-report.json

clean.sec: clean.bandit clean.safety ## Remove security reports
	rm -rf $(OUTPUT_DIR)/security

clean.package: package.clean ## Remove packaging build artifacts

clean.ratchetr: ## Clean Ratchetr caches
	rm -rf .ratchetr_cache
	rm -rf $(TYPING_REPORT_DIR)

clean: clean.caches clean.type clean.lint clean.test clean.sec ## Remove all local caches

clean.full: clean clean.package clean.ratchetr ## Remove all local caches and packaging


# ----------------------------------------------------------------------
##@ CI
# ----------------------------------------------------------------------

ci.check: ratchetr.all all.lint all.type test.cov all.sec ## Run ratchetr, lint, typing, tests (w/coverage), and security (CI parity)
	@echo "CI checks completed."

ci.package: package.build package.check ## Build and sanity-check distribution artifacts
	@echo "Packaging checks completed."

ci.all: ci.check ci.package ## Full CI: checks + packaging
	@echo "Full CI (checks + packaging) completed."


# ----------------------------------------------------------------------
##@ Pre-commit
# ----------------------------------------------------------------------

precommit.check: ## Run all pre-commit hooks on the repo
	$(UV) pre-commit run --all-files

precommit.update: ## Update pre-commit hooks to latest versions
	$(UV) pre-commit autoupdate

precommit.install: ## Install pre-commit hooks using uv
	$(UV) pre-commit install


# ----------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------

HELP_GROUP_FORMAT := "\n\033[1m%s\033[0m\n"
HELP_CMD_FORMAT   := "  \033[36m%-32s\033[0m %s\n"

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
	@printf $(HELP_CMD_FORMAT) "RATCHETR_FLAGS='...'" " Extra args forwarded to 'ratchetr audit'"
	@printf $(HELP_CMD_FORMAT) "VERIFYTYPES_DISABLED=1" " Skip pyright --verifytypes in 'type'"
	@printf "\nHint: run \033[36mmake <group>.help\033[0m for a specific group (e.g., 'test.help', 'lint.help', 'type.help').\n"

%.help:
	@awk 'BEGIN {FS=":.*##"} \
		/^[a-zA-Z0-9_.-•]+:.*##/ { printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep "^  .*$(firstword $(MAKECMDGOALS))\..*" || true
