MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c


# ----------------------------------------------------------------------
# Core tool wiring
# ----------------------------------------------------------------------

UV := uv run
PY := $(UV) python -m

OUTPUT_DIR           ?= out
SEC_DIR              ?= $(OUTPUT_DIR)/security
LINT_DIR		     ?= $(OUTPUT_DIR)/lint
TYPE_DIR		     ?= $(OUTPUT_DIR)/type

RATCHETR_DIR  	     ?= $(OUTPUT_DIR)/.ratchetr
MANIFEST_PATH        ?= $(RATCHETR_DIR)/manifest.json

RATCHETR_STATUSES    ?= blocked ready
RATCHETR_LEVEL       ?= folder
RATCHETR_LIMIT       ?= 20
# Extra flags forwarded directly to `ratchetr audit` (e.g., --root src/ratchetr)
RATCHETR_FLAGS       ?=

VERIFYTYPES_DISABLED ?= 0
VERIFYTYPES_PACKAGE  ?= ratchetr

.DEFAULT_GOAL := help

.PHONY: \
  all all.full all.test all.lint all.type all.format all.fix all.sec all.check all.ratchetr \
  lint lint.ruff lint.format lint.markdown lint.pylint lint.pylint.report \
  lint.fix lint.fix.ruff lint.fix.format lint.fix.markdown \
  type type.mypy type.pyright type.verifytypes type.clean \
  test test.verbose test.failfast test.unit test.integration test.property test.performance test.e2e test.smoke test.fast test.cov test.cov.report test.bench test.bench.report \
  test.clean test.clean.pytest test.clean.coverage test.clean.hypothesis test.clean.benchmarks \
  ratchetr ratchetr.audit ratchetr.dashboard ratchetr.dashboard.json ratchetr.readiness ratchetr.clean ratchetr.all \
  sec sec.lint sec.bandit sec.bandit.report sec.safety sec.safety.report \
  package.build package.check package.install-test package.clean \
  check check.license-headers check.error-codes check.ignores check.ignores.report \
  clean clean.pycache clean.cache clean.caches clean.mypy clean.pyright clean.type clean.ruff clean.pylint clean.lint \
  clean.coverage clean.pytest clean.hypothesis clean.benchmarks clean.test clean.pre-commit clean.precommit \
  clean.bandit clean.safety clean.sec clean.package clean.ratchetr clean.full \
  ci.check ci.package ci.all \
  precommit precommit.check precommit.update precommit.install precommit.clean \
  pre-commit pre-commit.check pre-commit.update pre-commit.install pre-commit.clean \
  find.% find.label.% %.find %.find.label find.help \
  help help.% %.help


# ----------------------------------------------------------------------
##@ Aggregate
# ----------------------------------------------------------------------

all.test: test ## Run full test suite
all.lint: lint ## Run all lint checks (ruff, pylint, markdown)
all.type: type ## Run mypy + pyright (+ verify-types unless VERIFYTYPES_DISABLED=1)
all.format: lint.format ## Check formatting (no changes)
all.fix: lint.fix ## Apply formatter and autofix lints
all.sec: sec ## Run all security checks
all.check: check ## Run all internal checks
all.ratchetr: ratchetr.all ## Run full Ratchetr report generation
all: all.lint all.type test.cov all.sec check.error-codes ## Run lint, typing, tests (w/coverage), security, and internal checks
	@printf "  =+= All checks completed =+=\n\n"
all.full: all.fix all all.ratchetr ## Run all checks, fixes, and report generation
	@printf "  =+= All full tasks completed =+=\n\n"


# ----------------------------------------------------------------------
##@ Lint & Format
# ----------------------------------------------------------------------

lint: lint.ruff lint.format lint.markdown lint.pylint ## Lint code and docs
	@printf "  =+= All lint checks completed =+=\n\n"

lint.ruff: ## Run ruff lint
	@printf "=+= Running ruff lint... =+=\n"
	$(UV) ruff check --preview
	@printf "=+= Ruff lint completed =+=\n\n"

lint.format: ## Check ruff formatting (no changes)
	@printf "=+= Checking ruff formatting... =+=\n"
	$(UV) ruff format --check
	@printf "=+= Ruff formatting check completed =+=\n\n"

lint.markdown: ## Run pymarkdownlnt on markdown files
	@printf "=+= Running pymarkdownlnt on markdown files... =+=\n"
	$(UV) pymarkdownlnt --strict-config scan -r -e "./.*/**/*.md" .
	@printf "=+= pymarkdownlnt run completed =+=\n\n"

lint.pylint: ## Run Pylint code quality checks
	@printf "=+= Running Pylint... =+=\n"
	$(UV) pylint src/ratchetr --output-format=colorized
	@printf "=+= Pylint run completed =+=\n\n"

lint.pylint.report: ## Run Pylint and write JSON report
	@printf "=+= Running Pylint (JSON report)... =+=\n"
	@mkdir -p $(LINT_DIR)
	$(UV) pylint src/ratchetr --output-format=json --reports=n > $(LINT_DIR)/pylint.json
	@printf "Pylint report: $(LINT_DIR)/pylint.json\n"
	@printf "=+= Pylint JSON report completed =+=\n\n"

lint.fix.ruff: ## Apply ruff formatter
	@printf "=+= Applying ruff safe autofixes... =+=\n"
	$(UV) ruff check --preview --fix
	@printf "=+= Ruff safe autofixes applied =+=\n\n"

lint.fix.format: ## Apply ruff formatter
	@printf "=+= Applying ruff formatting... =+=\n"
	$(UV) ruff format
	@printf "=+= Ruff formatting applied =+=\n\n"

lint.fix.markdown: ## Run pymarkdownlnt on markdown files
	@printf "=+= Applying markdown formatting... =+=\n"
	$(UV) pymarkdownlnt --strict-config fix -r -e "./.*/**/*.md" .
	@printf "=+= Markdown formatting applied =+=\n\n"

lint.fix: lint.fix.ruff lint.fix.format lint.fix.markdown ## Apply formatter and safe autofix lints
	@printf "  =+= All fixes applied =+=\n\n"


# ----------------------------------------------------------------------
##@ Typing
# ----------------------------------------------------------------------

type: type.mypy type.pyright type.verifytypes ## Run mypy + pyright (+ verify-types unless VERIFYTYPES_DISABLED=1)
	@printf "  =+= All typing checks completed =+=\n\n"

type.mypy: ## Run mypy
	@printf "=+= Running mypy... =+=\n"
	$(UV) mypy
	@printf "=+= Mypy run completed =+=\n\n"

type.pyright: ## Run pyright
	@printf "=+= Running pyright... =+=\n"
	$(UV) pyright
	@printf "=+= Pyright run completed =+=\n\n"

type.verifytypes: ## Verify public typing completeness via pyright (opt-out via VERIFYTYPES_DISABLED=1)
ifeq ($(VERIFYTYPES_DISABLED),0)
	@printf "=+= Running pyright --verifytypes for package: $(VERIFYTYPES_PACKAGE)... =+=\n"
	PYTHONPATH=src $(UV) pyright --verifytypes $(VERIFYTYPES_PACKAGE) --ignoreexternal
	@printf "=+= Pyright --verifytypes run completed =+=\n\n"
else
	@printf "=+= [skip] pyright --verifytypes disabled via VERIFYTYPES_DISABLED=1 (package: $(VERIFYTYPES_PACKAGE)) =+=\n\n"
endif

type.clean: clean.type ## Clean all typing caches


# ----------------------------------------------------------------------
##@ Tests
# ----------------------------------------------------------------------

test: ## Run pytest (quiet)
	@printf "=+= Running tests... =+=\n"
	$(UV) pytest -q
	@printf "=+= Test run completed =+=\n\n"

test.verbose: ## Run pytest verbosely
	@printf "=+= Running tests verbosely... =+=\n"
	$(UV) pytest -v
	@printf "=+= Verbose test run completed =+=\n\n"

test.failfast: ## Run pytest, stopping on first failure
	@printf "=+= Running tests with fail-fast... =+=\n"
	$(UV) pytest -x
	@printf "=+= Fail-fast test run completed =+=\n\n"

test.unit: ## Run unit tests (tests/unit)
	@printf "=+= Running unit tests... =+=\n"
	$(UV) pytest -q tests/unit
	@printf "=+= Unit tests completed =+=\n\n"

test.integration: ## Run integration tests (tests/integration)
	@printf "=+= Running integration tests... =+=\n"
	$(UV) pytest -q tests/integration
	@printf "=+= Integration tests completed =+=\n\n"

test.property: ## Run property-based tests (tests/property_based)
	@printf "=+= Running property-based tests... =+=\n"
	$(UV) pytest -q tests/property_based
	@printf "=+= Property-based tests completed =+=\n\n"

test.performance: ## Run performance tests (tests/performance)
	@printf "=+= Running performance tests... =+=\n"
	$(UV) pytest -q tests/performance
	@printf "=+= Performance tests completed =+=\n\n"

test.e2e: ## Run end-to-end tests (tests/e2e, marked e2e)
	@printf "=+= Running end-to-end tests... =+=\n"
	$(UV) pytest -q -m 'e2e' tests/e2e
	@printf "=+= End-to-end tests completed =+=\n\n"

test.smoke: ## Run smoke tests (marked smoke)
	@printf "=+= Running smoke tests... =+=\n"
	$(UV) pytest -q -m 'smoke'
	@printf "=+= Smoke tests completed =+=\n\n"

test.fast: ## Run fast test subset (unit+smoke, excluding slow/property/benchmarks)
	@printf "=+= Running fast tests (unit+smoke, no slow/property/benchmarks)... =+=\n"
	$(UV) pytest -q -m '(unit or smoke) and not slow and not benchmark and not property'
	@printf "=+= Fast tests completed =+=\n\n"

test.cov: ## Run pytest with coverage (95% gate) on src/ratchetr
	@printf "=+= Running tests with coverage... =+=\n"
	$(UV) pytest --cov=src/ratchetr --cov-report=term --cov-fail-under=95
	@printf "=+= Tests with coverage completed =+=\n\n"

test.cov.report: ## Run pytest with coverage and write reports under out/coverage
	@printf "=+= Running tests with coverage (with reports)... =+=\n"
	@mkdir -p $(OUTPUT_DIR)/coverage
	$(UV) pytest \
		--cov=src/ratchetr \
		--cov-report=term \
		--cov-report=xml:$(OUTPUT_DIR)/coverage/coverage.xml \
		--cov-report=html:$(OUTPUT_DIR)/coverage/htmlcov \
		--cov-fail-under=95
	@printf "Coverage XML: $(OUTPUT_DIR)/coverage/coverage.xml\n"
	@printf "Coverage HTML: $(OUTPUT_DIR)/coverage/htmlcov\n"
	@printf "=+= Tests with coverage + reports completed =+=\n\n"

test.bench: ## Run performance benchmarks (requires pytest-benchmark plugin)
	@printf "=+= Running performance benchmarks... =+=\n"
	$(UV) pytest tests/performance/benchmarks --benchmark-only
	@printf "=+= Performance benchmarks completed =+=\n\n"

test.bench.report: ## Run benchmarks and write JSON report to out/benchmarks/benchmarks.json
	@printf "=+= Running performance benchmarks (with report)... =+=\n"
	@mkdir -p $(OUTPUT_DIR)/benchmarks
	$(UV) pytest tests/performance/benchmarks --benchmark-only --benchmark-json=$(OUTPUT_DIR)/benchmarks/benchmarks.json
	@printf "Benchmark report: $(OUTPUT_DIR)/benchmarks/benchmarks.json\n"
	@printf "=+= Performance benchmarks + report completed =+=\n\n"

test.clean.pytest: clean.pytest ## Clean pytest cache
	@printf "=+= Pytest cache cleaned =+=\n\n"

test.clean.coverage: clean.coverage ## Clean coverage artifacts
	@printf "=+= Coverage artifacts cleaned =+=\n\n"

test.clean.hypothesis: clean.hypothesis ## Clean Hypothesis cache
	@printf "=+= Hypothesis cache cleaned =+=\n\n"

test.clean.benchmarks: clean.benchmarks ## Clean pytest-benchmark cache
	@printf "=+= Pytest-benchmark cache cleaned =+=\n\n"

test.clean: clean.test ## Clean all test caches and artifacts
	@printf "  =+= All test caches and artifacts cleaned =+=\n\n"


# ----------------------------------------------------------------------
##@ Ratchetr
# ----------------------------------------------------------------------

$(MANIFEST_PATH):  ## Generate Ratchetr audit manifest
	@printf "=+= Generating Ratchetr audit manifest at $(MANIFEST_PATH)... =+=\n"
	mkdir -p $(RATCHETR_DIR)
	$(UV) ratchetr audit \
		$(RATCHETR_FLAGS) \
		--manifest $(MANIFEST_PATH) \
		--readiness \
		$(foreach status,$(RATCHETR_STATUSES),--readiness-status $(status))
	@printf "=+= Ratchetr audit manifest generated at $(MANIFEST_PATH) =+=\n\n"

ratchetr: ratchetr.audit ratchetr.dashboard ratchetr.readiness ## Run all Ratchetr typing report generation steps
	@printf "  =+= All Ratchetr reports generated =+=\n\n"

ratchetr.audit: $(MANIFEST_PATH) ## Logical alias
	@printf "=+= Ratchetr audit manifest generated at $(MANIFEST_PATH) =+=\n\n"

ratchetr.dashboard: $(MANIFEST_PATH) ## Render Ratchetr dashboards (Markdown + HTML)
	@printf "=+= Generating Ratchetr dashboard reports... =+=\n"
	mkdir -p $(RATCHETR_DIR)
	$(UV) ratchetr dashboard --manifest $(MANIFEST_PATH) --format markdown --output $(RATCHETR_DIR)/dashboard.md
	$(UV) ratchetr dashboard --manifest $(MANIFEST_PATH) --format html     --output $(RATCHETR_DIR)/dashboard.html
	@printf "=+= Ratchetr dashboard reports: $(RATCHETR_DIR)/dashboard.{md,html} =+=\n\n"

ratchetr.dashboard.json: $(MANIFEST_PATH) ## Render Ratchetr dashboard in JSON format
	@printf "=+= Generating Ratchetr dashboard JSON report... =+=\n"
	mkdir -p $(RATCHETR_DIR)
	$(UV) ratchetr dashboard --manifest $(MANIFEST_PATH) --format json     --output $(RATCHETR_DIR)/dashboard.json
	@printf "=+= Ratchetr dashboard JSON report: $(RATCHETR_DIR)/dashboard.json =+=\n\n"

ratchetr.readiness: $(MANIFEST_PATH) ## Show Ratchetr readiness summary
	@printf "=+= Ratchetr Readiness View (level: $(RATCHETR_LEVEL), statuses: $(RATCHETR_STATUSES), limit: $(RATCHETR_LIMIT)): =+=\n"
	mkdir -p $(RATCHETR_DIR)
	$(UV) ratchetr readiness \
		--manifest $(MANIFEST_PATH) \
		--level $(RATCHETR_LEVEL) \
		$(foreach status,$(RATCHETR_STATUSES),--status $(status)) \
		--limit $(RATCHETR_LIMIT)
	@printf "=+= End of Ratchetr Readiness View =+=\n\n"

ratchetr.all: ratchetr ratchetr.dashboard.json ## Include json report format with full run
	@printf "  =+= All Ratchetr reports generated =+=\n\n"

ratchetr.clean: clean.ratchetr ## Remove Ratchetr caches and reports
	@printf "=+= Ratchetr caches and reports cleaned =+=\n\n"


# ----------------------------------------------------------------------
##@ Security
# ----------------------------------------------------------------------

sec: sec.lint sec.bandit sec.safety ## Run all security checks
	@printf "  =+= All security checks completed =+=\n\n"

sec.lint: ## Security lint via ruff S-rules
	@printf "=+= Running security lint via ruff... =+=\n"
	$(UV) ruff check --select S
	@printf "=+= Security lint completed =+=\n\n"

sec.bandit: ## Run Bandit security scanner
	@printf "=+= Running Bandit scan... =+=\n"
	mkdir -p $(OUTPUT_DIR)/security
	$(UV) bandit -c pyproject.toml -r src/
	@printf "=+= Bandit scan completed =+=\n\n"

sec.bandit.report: ## Run Bandit security scanner w/JSON report
	@printf "=+= Running Bandit scan... =+=\n"
	mkdir -p $(SEC_DIR)
	$(UV) bandit -c pyproject.toml -r src/ -f json -o $(SEC_DIR)/bandit-report.json
	@printf "Bandit report: $(SEC_DIR)/bandit-report.json\n"
	@printf "=+= Bandit scan completed =+=\n\n"

sec.safety: ## Run Safety dependency scanner
	@printf "=+= Running Safety scan... =+=\n"
	$(UV) safety scan
	@printf "=+= Safety scan completed =+=\n\n"

sec.safety.report: ## Run Safety dependency scanner
	@printf "=+= Running Safety scan... =+=\n"
	mkdir -p $(SEC_DIR)
	$(UV) safety scan --save-as json $(SEC_DIR)/safety-report.json
	$(PY) json.tool $(SEC_DIR)/safety-report.json > $(SEC_DIR)/tmp.json
	mv $(SEC_DIR)/tmp.json $(SEC_DIR)/safety-report.json
	@printf "Safety report: $(SEC_DIR)/safety-report.json\n"
	@printf "=+= Safety scan completed =+=\n\n"


# ----------------------------------------------------------------------
##@ Packaging
# ----------------------------------------------------------------------

package.build: ## Build sdist and wheel into dist/
	@printf "=+= Building distribution artifacts... =+=\n"
	$(PY) build
	@printf "=+= Distribution artifacts built in dist/ =+=\n\n"

package.check: ## Run Twine check on built artifacts
	@printf "=+= Checking distribution artifacts... =+=\n"
	$(UV) twine check dist/*
	@printf "=+= Distribution artifacts check completed =+=\n\n"

package.install-test: ## Install built wheel in a temporary venv to ensure installability
	@printf "=+= Testing installation of built wheel... =+=\n"
	$(UV) python scripts/install_test_wheel.py
	@printf "=+= Installation test completed =+=\n\n"

package.clean: ## Remove build artifacts
	@printf "=+= Cleaning build artifacts... =+=\n"
	$(UV) python scripts/clean_build_artifacts.py
	@printf "=+= Build artifacts cleaned =+=\n\n"


# ----------------------------------------------------------------------
##@ Internal checks
# ----------------------------------------------------------------------

check.error-codes: ## Verify error code registry and documentation are in sync
	@printf "=+= Checking error code registry and documentation... =+=\n"
	$(UV) python scripts/check_error_codes.py
	@printf "=+= Error code registry and documentation check completed =+=\n\n"

check.ignores: ## Verify that ignores (noqa, pylint, type: ignore, pyright, coverage) are justified
	@printf "=+= Checking ignore justifications... =+=\n"
	$(PY) scripts.check_ignores
	@printf "=+= Ignore justification check completed =+=\n\n"

check.ignores.report: ## Write ignore justification report
	@printf "=+= Generating ignore justification report... =+=\n"
	@mkdir -p $(LINT_DIR)
	$(PY) scripts.check_ignores --json > $(LINT_DIR)/ignores.json
	@printf "Ignore justification report: $(LINT_DIR)/ignores.json\n"
	@printf "=+= Ignore justification report completed =+=\n\n"

check.license-headers: ## Verify Apache 2.0 license headers in source files
	@printf "=+= Checking Apache 2.0 license headers in source files... =+=\n"
	$(UV) python scripts/check_license_headers.py
	@printf "=+= License header check completed =+=\n\n"

check: check.error-codes check.license-headers check.ignores ## Run all internal checks
	@printf "  =+= All internal checks completed =+=\n\n"

# ----------------------------------------------------------------------
##@ Cleaning
# ----------------------------------------------------------------------

clean.mypy: ## Remove mypy cache
	@printf "=+= Removing Mypy cache... =+=\n"
	rm -rf .mypy_cache
	@printf "=+= Mypy cache removed =+=\n\n"

clean.pyright: ## Remove pyright cache
	@printf "=+= Removing Pyright cache... =+=\n"
	rm -rf .pyrightcache
	@printf "=+= Pyright cache removed =+=\n\n"

clean.type: clean.mypy clean.pyright ## Remove typing caches
	@printf "  =+= All typing caches removed =+=\n\n"

clean.ruff: ## Remove ruff cache
	@printf "=+= Removing Ruff cache... =+=\n"
	rm -rf .ruff_cache
	@printf "=+= Ruff cache removed =+=\n\n"

clean.pylint: ## Remove pylint cache
	@printf "=+= Removing Pylint cache... =+=\n"
	rm -rf .pylint.d
	rm -f $(LINT_DIR)/pylint.json
	@printf "=+= Pylint cache removed =+=\n\n"

clean.lint: clean.ruff clean.pylint ## Remove lint caches
	rm -rf $(LINT_DIR)
	@printf "  =+= All lint caches removed =+=\n\n"

clean.pycache: ## Remove Python bytecode and __pycache__ dirs
	@printf "=+= Removing Python bytecode and __pycache__ directories... =+=\n"
	find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.py[co]' \) -delete
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@printf "=+= Python bytecode and __pycache__ directories removed =+=\n\n"

clean.cache: ## Remove .cache directories
	@printf "=+= Removing .cache directories... =+=\n"
	find . -type d -name .cache -prune -exec rm -rf {} +
	@printf "=+= .cache directories removed =+=\n\n"

clean.precommit: clean.pre-commit ## Remove .pre-commit cache
clean.pre-commit:
	@printf "=+= Cleaning pre-commit caches... =+=\n"
	find . -type d -name .pre-commit-cache -prune -exec rm -rf {} +
	@printf "=+= Pre-commit cache removed =+=\n\n"

clean.caches: clean.pycache clean.cache clean.pre-commit ## Remove all common caches
	@printf "  =+= All common caches removed =+=\n\n"

clean.coverage: ## Remove coverage artifacts
	@printf "=+= Removing coverage artifacts... =+=\n"
	rm -f .coverage
	rm -rf htmlcov
	@printf "=+= Coverage artifacts removed =+=\n\n"

clean.pytest: ## Clean test caches
	@printf "=+= Removing pytest caches... =+=\n"
	rm -rf .pytest_cache
	@printf "=+= Pytest caches removed =+=\n\n"

clean.hypothesis: ## Remove Hypothesis caches
	@printf "=+= Removing Hypothesis caches... =+=\n"
	rm -rf .hypothesis
	@printf "=+= Hypothesis caches removed =+=\n\n"

clean.benchmarks: ## Remove pytest-benchmark caches
	@printf "=+= Removing pytest-benchmark caches... =+=\n"
	find . -type d -name .benchmarks -prune -exec rm -rf {} +
	@printf "=+= Pytest-benchmark caches removed =+=\n\n"

clean.test: clean.pytest clean.coverage clean.hypothesis clean.benchmarks ## Remove test caches and coverage artifacts
	@printf "  =+= All test caches and artifacts removed =+=\n\n"

clean.bandit: ## Remove Bandit report
	@printf "=+= Removing Bandit report... =+=\n"
	rm -f $(SEC_DIR)/bandit-report.json
	@printf "=+= Bandit report removed =+=\n\n"

clean.safety: ## Remove Safety report
	@printf "=+= Removing Safety report... =+=\n"
	rm -f $(SEC_DIR)/safety-report.json
	@printf "=+= Safety report removed =+=\n\n"

clean.sec: clean.bandit clean.safety ## Remove security reports
	rm -rf $(SEC_DIR)
	@printf "  =+= All security reports removed =+=\n\n"

clean.package: package.clean ## Remove packaging build artifacts

clean.ratchetr: ## Clean Ratchetr caches
	@printf "=+= Cleaning Ratchetr caches and reports... =+=\n"
	rm -rf .ratchetr_cache
	rm -rf $(RATCHETR_DIR)
	@printf "=+= Ratchetr caches and reports removed =+=\n\n"

clean: clean.caches clean.type clean.lint clean.test clean.sec ## Remove all local caches
	@printf "  =+= All local caches removed =+=\n\n"

clean.full: clean clean.package clean.ratchetr ## Remove all local caches and packaging
	rm -rf $(OUTPUT_DIR)
	@printf "  =+= Full clean completed =+=\n\n"


# ----------------------------------------------------------------------
##@ CI
# ----------------------------------------------------------------------

ci.check: ratchetr.all all.lint all.type test.cov all.sec all.check ## Run ratchetr, lint, typing, tests (w/coverage), security, and internal checks (CI parity)
	@printf "=+= CI checks completed =+=\n\n"

ci.package: package.build package.check ## Build and sanity-check distribution artifacts
	@printf "=+= Packaging checks completed =+=\n\n"

ci.all: ci.check ci.package ## Full CI: checks + packaging
	@printf "=+= Full CI (checks + packaging) completed =+=\n\n"


# ----------------------------------------------------------------------
##@ Pre-commit
# ----------------------------------------------------------------------

precommit.clean: clean.pre-commit  ## Remove .pre-commit cache
pre-commit.clean: clean.pre-commit

pre-commit.check: ## Run all pre-commit hooks on the repo
	@printf "=+= Running pre-commit on all files... =+=\n"
	$(UV) pre-commit run --all-files
	@printf "=+= Pre-commit checks completed =+=\n\n"

pre-commit.update: ## Update pre-commit hooks to latest versions
	@printf "=+= Updating pre-commit... =+=\n"
	$(UV) pre-commit autoupdate
	@printf "=+= Pre-commit hooks updated =+=\n\n"

pre-commit.install: pre-commit.install
pre-commit.install: ## Install pre-commit hooks using uv
	@printf "=+= Installing pre-commit hooks... =+=\n"
	uv run pre-commit install
	uv run pre-commit install --hook-type pre-push
	@printf "=+= Pre-commit hooks installed =+=\n\n"

precommit: pre-commit
pre-commit:
	@printf "=+= Running pre-commit on all files... =+=\n"
	uv run pre-commit run --all-files --show-diff-on-failure
	@printf "=+= Pre-commit checks completed =+=\n\n"


# ----------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------

HELP_GROUP_FORMAT := "\n\033[1m%s\033[0m\n\n"
HELP_CMD_FORMAT   := "  \033[36m%-32s\033[0m %s\n\n"

help:
	@printf $(HELP_GROUP_FORMAT) "Ratchetr Makefile Commands\n"
	@printf $(HELP_GROUP_FORMAT) "Usage:\n"
	@printf "  \033[36m%s\033[0m%s\033[36m%-26s\033[0m%s\n\n" "make " "or" " make help" " View this help message\n"
	@awk 'BEGIN {FS=":.*##"} \
		/^##@/ { printf $(HELP_GROUP_FORMAT), substr($$0,5); next } \
		/^[a-zA-Z0-9_.-•]+:.*##/ { printf $(HELP_CMD_FORMAT), $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@printf "\n\n\n"
	@printf $(HELP_GROUP_FORMAT) "Common arguments (override per call):\n"
	@printf $(HELP_CMD_FORMAT) "RATCHETR_LEVEL=folder|file" " Scope readiness view\n"
	@printf $(HELP_CMD_FORMAT) "RATCHETR_STATUSES=blocked\ ready" " Filter readiness statuses\n"
	@printf $(HELP_CMD_FORMAT) "RATCHETR_LIMIT=20" " Limit entries in readiness view\n"
	@printf $(HELP_CMD_FORMAT) "RATCHETR_FLAGS='...'" " Extra args forwarded to 'ratchetr audit'\n"
	@printf $(HELP_CMD_FORMAT) "VERIFYTYPES_DISABLED=1" " Skip pyright --verifytypes in 'type'\n"
	@printf "\nHints:\n- Run \033[36mmake <group>.help\033[0m for a specific group (e.g., 'test.help').\n- Run find.help for search help.\n\n\n"

%.help:
	@$(UV) python scripts/make_help.py "$*" "$(firstword $(MAKEFILE_LIST))"

help.%:
	@$(UV) python scripts/make_help.py "$*" "$(firstword $(MAKEFILE_LIST))"


# ----------------------------------------------------------------------
##@ Find
# ----------------------------------------------------------------------

FIND_SCRIPT := scripts/make_find.py

# Full-text search:
#   make find.lint
#   make find.lint.cov             # same as: make find."lint cov"
#   make find."python+3.11"
find.%: ## Full-text search Makefile help (labels, names, descriptions)
	$(UV) python $(FIND_SCRIPT) $(subst ., ,$*)

%.find: ## Full-text search Makefile help (labels, names, descriptions)
	$(UV) python $(FIND_SCRIPT) $(subst ., ,$*)

# Label-oriented search (section headings + command names):
#   make find.label.tests
#   make find.label.lint.ruff      # same as: make find.label."lint ruff"
#   make find.label."lint+ruff"
find.label.%: ## Label-only search (section slugs, labels, and command names)
	$(UV) python $(FIND_SCRIPT) --labels-only $(subst ., ,$*)

%.find.label: ## Label-only search (section slugs, labels, and command names)
	$(UV) python $(FIND_SCRIPT) --labels-only $(subst ., ,$*)

find.help: ## Show usage examples for find.* search helpers
	@printf "\nFind / search helpers (dot-notation only):\n\n\n"
	@printf "  make find.<query>              Full-text search (labels, names, descriptions)\n\n"
	@printf "  make find.lint                 Search for 'lint'\n\n"
	@printf "  make find.lint.cov             OR search: 'lint' OR 'cov'\n\n"
	@printf "  make find.\"python+3.11\"        AND search: 'python' AND '3.11'\n\n"
	@printf "\n  make find.label.<query>        Label-oriented search (heading + command names)\n\n"
	@printf "  make find.label.test           Commands whose heading/name contains 'test'\n\n"
	@printf "  make find.label.lint.ruff      Commands with 'lint' OR 'ruff' (dot as OR)\n\n"
	@printf "  make find.label.\"lint+ruff\"    Commands whose heading/name contains both\n\n"
	@printf "\nQuery semantics:\n\n"
	@printf "  - Dots and spaces act like OR separators (handled via $(subst ., ,$*)).\n\n"
	@printf "  - '+' inside a term acts as an AND separator (e.g., 'test+clean').\n\n"
	@printf "  - In label mode, each command is matched against '<slug> <label> <name>'.\n\n"
	@printf "    Only commands where this combined text satisfies the query are shown.\n\n"
	@printf "\nNotes:\n\n"
	@printf "  - Avoid 'make find foo' (without a dot); only 'find.<query>' and\n\n"
	@printf "    'find.label.<query>' are wired.\n\n"

find: ## Guard target: dot-notation only (see `make find.help`)
	@printf "\n[find] Unsupported invocation.\n\n\n"
	@printf "Dot-notation usage only:\n\n"
	@printf "  make find.<query>           Full-text search (labels, names, descriptions)\n\n"
	@printf "  make find.label.<query>     Label-oriented search (heading + command names)\n\n"
	@printf "\nExamples:\n\n"
	@printf "  make find.clean.test        # search for 'clean' OR 'test'\n\n"
	@printf "  make find.\"clean test\"      # same as above\n\n"
	@printf "  make find.\"clean+test\"      # 'clean' AND 'test'\n\n"
	@printf "  make find.label.test.clean  # labels/names with 'test' OR 'clean'\n\n"
	@printf "\nFor more details: make find.help\n\n\n"
	@exit 1
