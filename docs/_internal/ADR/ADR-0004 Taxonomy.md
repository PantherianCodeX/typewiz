# ADR-0004: Repository Taxonomy and Directory Structure

**Status:** Accepted
**Date:** 2025-12-15
**Deciders:** Ratchetr maintainers
**Technical Story:** N/A (foundational repository taxonomy for pre-release)

## Context and Problem Statement

Ratchetr’s codebase already spans multiple concerns: CLI presentation, configuration ingestion, engine execution, artifact construction (manifest/dashboards), persistence orchestration, and supporting infrastructure. In ratchetr-0.1.0-dev-3, the repository contains the core package under `src/ratchetr/`, supporting assets (`schemas/`, `typings/`, `scripts/`, `docs/`, `examples/`), and a multi-suite test pyramid (`tests/`).

Without a precise, enforceable taxonomy, structure drift becomes likely:

* “Convenience” placement of logic in inappropriate layers (especially shims/helpers).
* Dependency cycles between CLI, services, and feature packages.
* A “shared utils” grab-bag replacing deliberate modularity.
* Tests that no longer mirror product boundaries, making coverage placement arbitrary.
* Generated artifacts and build outputs being committed into source trees.

This ADR defines **taxonomy and directory structure only**: package roles, layering rules, allowed dependency directions, and test layout. Behavioral policy (CLI semantics, precedence, scoping, planning) is explicitly out of scope.

## Decision Drivers

* **Layer separation:** clear ownership boundaries and one-way dependencies.
* **Cycle avoidance:** prevent CLI ↔ feature coupling and similar structural hazards.
* **Curated sharing:** allow DRY refactors without creating a “misc utils” dumping ground.
* **Repo hygiene:** keep generated artifacts and build outputs out of `src/` and out of VCS.
* **Test discoverability:** tests should mirror product domains and suite intent.

## Considered Options

1. **Ad hoc placement** (feature-local by default, occasional shared helpers wherever convenient).
2. **Central “shared utils/common” hub** for cross-cutting code.
3. **Layered taxonomy with curated shared package(s) and explicit boundary packages** (chosen).

## Decision Outcome

**Chosen Option:** Adopt a **layered repository taxonomy** with explicit directory roles, constrained dependency directions, and a curated cross-feature sharing strategy because the feature complexity and risk is too high for ad-hoc or centralized placements.

### High-level structure

#### Target Taxonomy (repository tree)

```text
.
├── .github/
│   └── workflows/                 # CI/CD automation (GitHub Actions)
│       ├── ci.yml                 # PR + main validation
│       ├── nightly.yml            # scheduled verification
│       └── release.yml            # release/publish automation
├── docs/                          # internal and public-facing documentation
├── examples/                      # examples only
├── schemas/                       # JSON Schema contracts (external contracts)
├── scripts/                       # repo tooling scripts (non-runtime)
├── src/
│   └── ratchetr/                  # runtime package
│       ├── __init__.py            # canonical public API surface (strict façade)
│       ├── __main__.py            # entrypoint
│       ├── cli/                   # presentation layer
│       ├── services/              # orchestration layer
│       ├── config/                # config ingestion + validation boundary
│       ├── core/                  # shared vocabulary
│       ├── compat/                # compatibility shims (leaf-like)
│       ├── _infra/                # private infrastructure (non-public API)
│       │   └── helpers/           # dependency-safe infrastructure helpers
│       ├── common/                # curated cross-feature helpers (small)
│       ├── adapters/              # boundary translation (external representations)
│       ├── engines/               # engine interfaces + registry + builtins
│       └── <feature-packages>/    # audit/, manifest/, dashboard/, ratchet/, readiness/, ...
├── tests/                         # test pyramid suites + fixtures + helpers
└── typings/                       # third-party typing stubs (tooling only)
```

**Notes:**

* **Private infrastructure naming:** The private infrastructure package is named `_infra/` (previously `_internal/`) to clearly communicate its role as **infrastructure**, not “misc internal code.” `_infra/` remains private and non-public API.
* **Private infrastructure helper naming:** The helper package is named `_infra/helpers/` (previously `_infra/utils/`) to align it with naming conventions utilized in other areas of the codebase.

### Layering and dependency direction

This taxonomy enforces **one-way dependencies** to prevent cycles and keep responsibilities local. The key principle is: **presentation → orchestration → domain**, with shared vocabulary and compatibility as dependency-light foundations.

### Layering diagram (primary dependency flow)

```text
┌─────────────────────┐
│ cli/                │  Presentation: args, formatting, exit codes
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ services/            │  Orchestration: workflows + side-effect coordination
└─────┬─────────┬─────┘
      │         │
      │         ├───────────────────────────────┐
      │         │                               │
      ▼         ▼                               ▼
┌───────────┐  ┌────────────┐                ┌────────────┐
│ features/ │  │ engines/   │                │ adapters/  │
│ (domain)  │  │ (execution)│                │ (boundary) │
└─────┬─────┘  └─────┬──────┘                └──────┬─────┘
      │              │                              │
      └──────┬───────┴──────────────┬───────────────┘
             ▼                      ▼
      ┌──────────────┐        ┌──────────────┐
      │ core/        │        │ config/      │
      │ vocabulary   │        │ ingest+valid │
      └──────┬───────┘        └──────┬───────┘
             ▼                       ▼
        ┌──────────┐          ┌──────────────┐
        │ compat/  │          │ _infra/      │  Private infrastructure
        │ leaf-like│          │ + helpers/   │  (dependency-safe)
        └──────────┘          └──────────────┘

(common/ exists as a small curated helper area only when required to avoid cycles)
```

### Allowed dependency directions (rules)

#### Presentation and orchestration

* `cli/` may depend on: `services/`, `config/`, `core/`, `compat/`, and strict façade exports (`ratchetr/*.py` façade modules).
* `cli/` must not depend on: feature packages (domain semantics), `engines/` execution internals, or `adapters/`.

#### Orchestration

* `services/` may depend on: feature packages, `engines/`, `adapters/`, `config/`, `core/`, `compat/`, `common/`, `_infra/`.

#### Domain

* Feature packages may depend on: `core/`, `compat/`, `config/` (for typed config values only), `_infra/helpers/` (infrastructure utilities), and `common/` (curated, when necessary).
* Feature packages should not depend directly on other feature packages except via shared types in `core/` or curated helpers in `common/`. Cross-feature workflows belong in `services/`.
* Feature packages must not depend on `adapters/`. Boundary translation is an edge concern and is consumed by `services/` (and narrowly by `engines/` where tool I/O requires it).

#### Engines

* `engines/` may depend on: `core/`, `compat/`, `config/` (typed engine settings), `_infra/helpers/`, and narrowly on `common/` if required to prevent cycles.
* `engines/` may depend on `adapters/` only for tool/vendor representation translation as part of engine I/O (representation-focused only).
* `engines/` must not depend on: `cli/` or `services/`.

#### Boundary translation

* `adapters/` may depend on: `core/`, `compat/`, and feature-owned *types* as needed to map representations.
* `adapters/` must not depend on: `cli/` or `services/`.
* `adapters/` is consumed by `services/` as the primary boundary translator; `cli/` and feature packages do not call adapters directly.

#### Foundations

* `compat/` is dependency-leaf-like: it must not import from higher layers.
* `_infra/` and `_infra/helpers/` must not import from `cli/` and must remain dependency-safe. `_infra/helpers/` is infrastructure-only and must not embed domain meaning.
* `common/` must remain small and dependency-safe; it exists only to avoid dependency direction problems and must not become a general-purpose “shared utils” hub.

### Visual: permitted vs prohibited imports (quick guide)

```text
PERMITTED (typical):
cli/ -> services/
cli/ -> config/ -> core/ -> compat/
services/ -> features/ + engines/ + adapters/
features/ -> core/ + compat/ + config/ + _infra/helpers/
engines/ -> core/ + compat/ + config/ + _infra/helpers/
adapters/ -> core/ + compat/ + feature types

PROHIBITED (typical):
features/ -> cli/ or services/
engines/  -> cli/ or services/
adapters/ -> cli/ or services/
compat/   -> anything above compat/
features/ -> adapters/ (boundary translation is not a domain dependency)
cli/      -> adapters/ (CLI must call services, not boundary translation)
root façade modules -> substantive implementation logic
```

---

#### Module Placement Decision Tree

```text
Is it user-facing CLI parsing/printing?        -> cli/
Is it workflow coordination or persistence?    -> services/
Is it feature semantics / domain rules?        -> <feature package>/
Is it tool execution/registry/builtin engine?  -> engines/
Is it config parsing/validation/loading?       -> config/
Is it cross-feature vocabulary?                -> core/
Is it cross-version shim/backport?             -> compat/
Is it private infrastructure utility?          -> _infra/helpers/
Is it cross-feature helper that avoids cycles? -> common/ (rare, curated)
Is it external representation translation?     -> adapters/
```

### Taxonomy rules for `src/ratchetr/`

#### 1) Package root modules (`src/ratchetr/*.py`) — strict façade

**Role:** the strict public façade for ratchetr. Root modules exist to define and expose the supported public API and entrypoints, not to host implementations.

**Allowed:**

* **Façade modules** that only re-export public symbols from internal implementations or feature/service modules.
* Minimal entrypoints (`__main__.py`) that delegate to CLI wiring.
* `__init__.py` as the canonical public API surface, with explicit `__all__`.

**Prohibited:**

* Substantive implementation logic (helpers, algorithms, parsing/normalization utilities, policy decisions).
* Domain logic (audit/ratchet/readiness semantics, planning semantics).
* Boundary translation logic (belongs in `adapters/`).
* Compatibility shims and backports (belongs in `compat/`).
* CLI command wiring/presentation (belongs in `cli/`).

**Hard rules (enforced by convention and review):**

* Every façade module must:

  * Define `__all__`
  * NOT contain reusable implementation
  * NOT contain policy logic
  * NOT import from `cli/`
* Runtime logic is limited to trivial re-export wiring and typing-only scaffolding.
* Reusable implementations belong in `_infra/helpers/` or an owning feature package, then optionally re-exported.

**Why:** the root package is the most visible import surface and the most expensive to refactor later. Keeping it strict prevents “utility creep,” reduces coupling, and makes it unambiguous what is public vs internal.

##### 1.1 Public exports vs internal implementations

**Canonical public API:**

* `ratchetr/__init__.py` is the canonical export list for the library API.
* Additional façade modules at root (e.g., `ratchetr.paths`, `ratchetr.cache`) exist only when they represent intentional, stable, user-facing entrypoints.

**Internal implementations:**

* Implementations live under `_infra/`, feature packages, or `services/`.
* `_infra/` is private by taxonomy; it may change without notice and is not part of the stable public API.

**Separation rule:**

* If a symbol is re-exported at the root, it is considered part of the supported public surface.
* If a symbol is not re-exported, it is internal (even if technically importable in Python).

**Why:** this creates a clear and reviewable definition of “public” without relying on informal expectations.

#### 1.2 Compatibility shims placement (`compat/` only)

**Rule:** compatibility shims do not belong in the root façade.

* Cross-version and backport logic lives under `ratchetr/compat/`.
* Runtime code imports compatibility constructs from `ratchetr.compat` (or `ratchetr.compat.<module>`), not from root-level shims.

**Why:** `compat/` already provides a single source of truth for backports. Adding root-level compat shims duplicates concerns, expands public surface area, and invites inconsistent imports across the codebase.

#### 2) `cli/` (presentation layer)

**Role:** argument parsing, user-facing formatting, exit codes, and command dispatch.

**Allowed:**

* Command modules (`cli/commands/*`) and argument registration (`cli/helpers/*`).
* CLI-only helper utilities that shape raw input into specifications passed into services, without embedding domain rules.
* Output formatting for stdout/stderr (human-readable summaries and structured stdout formats).

**Prohibited:**

* Domain logic for audit/ratchet/manifest/readiness semantics.
* Persistence orchestration and file I/O (belongs in `services/`).
* Engine execution logic and tool invocation (belongs in `engines/` and orchestrated by `services/`).

**Why:** CLI should remain replaceable and thin; domain behavior must not depend on UX pathways.

#### 3) `services/` (orchestration layer)

**Role:** application orchestration and side-effect boundaries (file I/O coordination, persistence gating, and multi-feature composition).

**Allowed:**

* Coordinating feature modules into cohesive operations (e.g., run → aggregate → persist).
* Owning “where side effects happen” (writes, cache save, output emission coordination, dry-run gating).
* Translating specifications and resolved values into executable sequences without redefining feature semantics.

**Prohibited:**

* CLI parsing/presentation.
* Embedding feature semantics that should live in the owning feature package.
* Tool-specific parsing/translation (belongs in engines/tool adapters).

**Why:** services are the application API; they provide predictable orchestration points and keep side effects centralized.

#### 4) Feature packages (domain logic)

Observed feature packages in dev-3:

* `audit/`, `dashboard/`, `manifest/`, `ratchet/`, `readiness/`

**Role:** domain logic and feature-owned structures.

**Allowed:**

* Feature-local runtime code and invariants (the “meaning” of the feature).
* Feature-owned typed schemas and validation models when they are intrinsic to the feature’s artifacts and computations.
* Feature-local helpers and utilities that primarily serve that feature.

**Prohibited:**

* CLI concerns and user interaction flows.
* Cross-feature “general utilities” unless promoted deliberately via the curated sharing rule (`common/`) or placed as infrastructure (`_infra/helpers/`).

**Why:** features are the semantic authority. Consolidating semantics prevents duplication and hidden divergence.

#### 5) `config/` (configuration ingestion boundary)

**Role:** parse, validate, and normalize configuration inputs into typed, internal configuration structures. This package is the **ingestion boundary** for config files and environment configuration.

**Allowed:**

* Configuration models and validation (`models.py`, `validation.py`).
* Configuration loading/parsing utilities (`loader.py`), including file reading and decoding (e.g., TOML parsing).
* Constants that define config keys and schema-related metadata (`constants.py`), where they are configuration-specific.
* Producing a typed configuration object suitable for consumption by `services/`, feature packages, and `engines/`.

**Prohibited:**

* CLI presentation concerns (argument parsing, formatting, exit codes).
* Orchestration concerns (deciding when/how to persist artifacts, coordinating workflow execution).
* Feature semantics (audit/ratchet/readiness rules) and policy decisions not intrinsic to parsing/validation.
* Engine execution logic (belongs in `engines/`).

**Dependency constraints:**

* `config/` may depend on: `core/`, `compat/`, and dependency-safe infrastructure in `_infra/helpers/`.
* `config/` must not depend on: `cli/`, `services/`, feature packages, `engines/` execution internals, or `adapters/`.

**Defaults boundary:**

* **Parsing defaults are allowed**: defaults required to construct a valid typed configuration shape (e.g., missing keys → empty collections, absent optional fields → `None`, schema-level defaults that preserve type invariants).
* **Behavioral defaults are prohibited**: defaults that define “what ratchetr does” operationally (e.g., selection semantics, precedence beyond representing inputs, persistence decisions, ratcheting policy). Behavioral interpretation belongs in `services/` and/or feature packages.

**Why:** configuration is a shared input boundary. Keeping it dependency-light avoids cycles and prevents policy from being embedded in parsing/validation code.

#### 6) `core/` (shared vocabulary)

**Role:** cross-feature types and shared primitives that are stable and broadly reused.

**Allowed:**

* Shared enums and categories used across multiple features.
* Small, stable primitives (aliases/newtypes) that unify vocabulary across the repo.
* Shared typed shapes only when they are truly cross-cutting.

**Constraints:**

* Keep `core/` dependency-light and low churn.
* Avoid moving feature-owned concepts into `core/` for convenience; prefer feature-local definitions.

**Why:** `core/` is imported everywhere; instability or feature bleed here amplifies coupling and refactor cost.

#### 7) `compat/` (compatibility layer)

**Role:** cross-version/platform compatibility shims (single source of truth for backports used across the repo).

**Allowed:**

* Backports and compatibility wrappers (typing helpers, small stdlib-equivalent shims).
* Narrow runtime normalization for availability differences (stdlib-first, backport fallback).

**Prohibited:**

* Domain semantics, policy logic, or feature behavior.
* Imports from `cli/`, `services/`, or feature packages (keep `compat/` dependency-leaf-like).
* Root-level “mirrors” of compat symbols (root stays façade-only).

**Why:** centralizing compatibility avoids scattered conditional imports and keeps version/platform variability contained and testable.

#### 8) `_infra/` and `_infra/helpers/` (private infrastructure)

**Role:** private implementation details behind public shims and low-level infrastructure utilities. `_infra/` is not public API.

**Allowed:**

* Dependency-safe helpers intended to be imported widely (`_infra/helpers/*`): process helpers, filesystem primitives (atomic writes, locking), small path utilities, deterministic ordering helpers (generic), and other infrastructure concerns that are domain-agnostic.
* Internal implementations behind root shims (cache primitives, path resolution primitives, low-level wiring utilities).

**Prohibited:**

* CLI presentation and command wiring.
* Feature/business logic and domain semantics (audit/manifest/dashboard/ratchet/readiness meaning).
* Boundary translation concerns (belongs in `adapters/`).

**Hard rule: `_infra/helpers/` is infrastructure-only**

* `_infra/helpers/` must not encode domain meaning or artifact semantics.
* `_infra/helpers/` must remain dependency-safe: it must not import from `cli/`, `services/`, feature packages, `engines/`, or `adapters/`.

**Import discipline:**

* Non-`_infra/` modules should consume public shims when available, rather than importing `_infra/*` directly.

**Why:** `_infra/` exists to keep implementation private while preserving a stable public surface; constraining it to infrastructure prevents “private” from becoming a catch-all.

#### 9) `common/` (curated cross-feature helpers)

**Role:** prevent dependency cycles when a helper must be shared between otherwise-independent layers or features.

**Allowed:**

* Small, stable utilities that are **truly cross-feature** and cannot be placed in a single owning package without creating an undesirable dependency direction or cycle.
* “Glue” helpers that may be domain-aware but are not owned by one feature and are used across at least two distinct packages.

**Key rule:** `common/` is not a “shared utilities” hub. It exists only when **all** of the following are true:

1. The helper is consumed by **at least two** distinct packages (e.g., two feature packages, or a feature and engines/services).
2. No single feature package can own it **without** introducing an undesirable dependency direction or cycle.
3. The helper is small, stable, and not merely “convenient.”

**Documentation rule (enforced by convention and review):**

* Every `common/*` module must include a brief module-level header explaining:

  * why it cannot live in a single owning package, and
  * which packages are its intended consumers.

**Prohibited:**

* General-purpose “misc utilities,” convenience shims, or duplication of `_infra/helpers/` infrastructure primitives.
* Feature-local helpers that have a natural owner (those belong in the owning feature package).

**Why:** curated sharing enables DRY without collapsing architecture into a generic utils bucket.

#### 10) `adapters/` (boundary package for external representations)

**Role:** boundary translation between internal domain structures and external representations (persisted payloads, schema-aligned shapes, tool/vendor mapping glue).

**Allowed:**

* Pure conversion/mapping code (encode/decode, to/from external payload shapes).
* External contract normalization (schema alignment, version bridging) when it is strictly about representation, not domain meaning.
* Boundary-only validation models when they exist to validate/shape external payloads at the boundary.

**Prohibited:**

* Internal domain semantics (audit/ratchet/readiness meaning, planning rules).
* Persistence orchestration (writes belong in `services/`).
* CLI user interaction logic.

**Dependency constraints:**

* `adapters/` may depend on: `core/`, `compat/`, and feature-owned *types* as needed to map representations.
* `adapters/` must not depend on: `cli/` or `services/`.
* `adapters/` must not import feature behavior modules for operational logic; it may import feature-owned types only for mapping.

**Consumption constraints (who may import adapters):**

* `services/` is the primary consumer of `adapters/` for persistence and external representation shaping.
* `engines/` may consume `adapters/` only when translating tool/vendor representations as part of engine I/O, and must keep that usage representation-focused.
* `cli/` and feature packages must not import `adapters/` directly.

**Why:** keeping representation translation isolated prevents external contract concerns from leaking into domain layers and preserves clean dependency direction.

---

### Taxonomy rules for repository-level directories (outside `src/`)

#### `schemas/`

**Role:** JSON Schema contracts for persisted artifacts (external-facing contracts).

**Allowed:**

* Versioned JSON Schema files for artifacts ratchetr emits or consumes (e.g., manifest/ratchet schemas).
* Supporting schema assets required to validate those artifacts.

**Prohibited:**

* Runtime Python implementations.
* Business/domain logic (belongs under `src/ratchetr/`).
* Test fixtures that are not schema contracts (belongs under `tests/fixtures/` or `tests/fixtures/snapshots/`).

**Why:** schemas represent stable interoperability contracts and must remain clearly separated from runtime code.

---

#### `typings/`

**Role:** type checker stubs for third-party libraries that do not provide (or do not sufficiently provide) typing.

**Allowed:**

* `.pyi` stubs and supporting typing metadata used by pyright/mypy/pylint.
* Minimal, narrowly-scoped stubs aligned to what ratchetr imports.

**Prohibited:**

* Runtime implementations (no `.py` logic intended for execution).
* Project/domain types (belongs under `src/ratchetr/`).

**Why:** `typings/` is tooling infrastructure; keeping it separate prevents accidental runtime coupling and keeps stub maintenance targeted.

---

#### `scripts/`

**Role:** developer tooling and repository maintenance utilities.

**Allowed:**

* One-off or developer-run scripts (lint helpers, repo checks, maintenance tasks).
* Automation helpers used by CI or Make targets, where appropriate.

**Prohibited:**

* Being imported by runtime package code under `src/ratchetr/`.
* Becoming a de facto library of runtime utilities (those belong in `_infra/helpers/` or feature packages).

**Why:** scripts have different constraints (may use heavier dependencies, repo-local assumptions) and must not influence runtime behavior or packaging.

---

#### `docs/`

**Role:** documentation, design notes, and ADRs.

**Allowed:**

* ADRs, architecture notes, user/developer guides, release notes.
* Static assets used for documentation (diagrams, images).

**Prohibited:**

* Runtime code.
* Test fixtures (unless specifically documentation examples and clearly scoped as such).

**Why:** keeps project governance and user guidance discoverable and separate from executable code.

---

#### `examples/`

**Role:** example configurations and minimal example projects for demonstration and manual testing.

**Allowed:**

* Sample config files and sample invocation patterns.
* Minimal example project structures demonstrating intended usage.

**Prohibited:**

* Production defaults (examples must not become a second configuration system).
* Test fixtures that should be validated in CI as part of the test suite (belongs under `tests/`).

**Why:** examples are educational; keeping them separate avoids confusing “sample” with “source of truth” and prevents accidental coupling to runtime behavior.

---

#### `.github/`

**Role:** CI/CD and repository automation (GitHub Actions workflows and supporting metadata).

**Allowed:**

* Workflow definitions under `.github/workflows/` (CI, nightly checks, release automation).
* Repository automation configuration and metadata required for GitHub integration.

**Prohibited:**

* Runtime package code or reusable project library code.
* Tooling scripts that should live in `scripts/`.
* Project documentation that should live in `docs/`.

**Why:** `.github/` is operational infrastructure for the repository. Keeping it isolated prevents automation details from leaking into runtime concerns and clarifies where build/release behavior is defined.

### Test taxonomy (`tests/`)

**Repository contract:** the test suite is a pyramid of suites with explicit intent. Suites are separated to preserve fast feedback loops (unit), validate composition (integration), protect the UX contract (e2e), and cover invariants and non-functional requirements (property/performance). Test **data artifacts** and test **code utilities** are separated to keep taxonomy crisp.

#### Desired directory tree (target taxonomy)

```text
tests/
├── unit/                          # fast, deterministic, domain-mirrored unit tests
│   ├── core/
│   ├── compat/
│   ├── config/
│   ├── _infra/                    # only if private infrastructure modules are tested directly
│   ├── engines/
│   │   ├── builtin/
│   │   └── registry/
│   ├── audit/
│   ├── manifest/
│   ├── dashboard/
│   ├── readiness/
│   ├── ratchet/
│   ├── services/                  # minimal; prefer integration for workflows
│   ├── cli/                       # parsing/formatting units (no end-to-end)
│   └── common/                    # only tests for src/ratchetr/common/*
├── integration/                   # multi-package composition tests (service workflows)
│   ├── audit/
│   ├── engines/
│   ├── manifest/
│   ├── dashboard/
│   ├── ratchet/
│   ├── readiness/
│   └── services/
├── e2e/                           # end-to-end workflows (CLI-level)
│   ├── audit/
│   ├── dashboard/
│   ├── ratchet/
│   └── cli/
├── property/                      # property-based tests (Hypothesis)
│   ├── paths/                     # normalization/scoping invariants
│   ├── serialization/             # round-trip invariants where applicable
│   └── invariants/                # determinism/ordering and other invariants
├── performance/                   # benchmarks/micro-perf (isolated; may be optional in CI)
│   ├── scoping/
│   ├── rendering/
│   └── aggregation/
├── fixtures/                      # shared test data artifacts (NOT code)
│   ├── data/                      # static inputs used by tests (configs, sample trees)
│   ├── tool_outputs/              # captured/stubbed tool outputs as data files
│   └── snapshots/                 # canonical golden files (ONLY snapshot location)
│       ├── manifest/
│       ├── dashboard/
│       └── ratchet/
└── helpers/                       # shared test code utilities (NOT runtime code)
    ├── builders/                  # object builders/factories
    ├── fakes/                     # fake implementations (in-memory cache, fake runners)
    └── assertions/                # shared assertion helpers (optional)
```

**Notes:**

* “Builders” are **helpers** (test code), not fixtures. Fixtures are **data artifacts**.
* Pytest fixture functions should live near the tests that use them or in suite-level `conftest.py` files; they do not belong under `tests/fixtures/`.

---

#### `tests/unit/`

**Role:** fast, deterministic unit tests scoped to a single module/package boundary.

**Allowed:**

* Tests that exercise one primary unit (function/class/module) with controlled collaborators.
* Domain-mirrored placement: `tests/unit/<package>/...` maps to `src/ratchetr/<package>/...`.

**Prohibited:**

* Cross-feature workflows and filesystem-heavy tests (belongs in integration or e2e).
* Long-running or flaky tests.

**Rule:** Unit tests must mirror product domains; catch-all folders (`misc/`, `utilities/`, `models/`) are not used.

**Why:** mirroring taxonomy makes test placement and ownership unambiguous.

---

#### `tests/integration/`

**Role:** validate behavior across multiple packages with real wiring (but not full CLI end-to-end).

**Allowed:**

* Service orchestration tests composing multiple features.
* Controlled filesystem I/O where required (prefer temporary directories).

**Prohibited:**

* Full CLI end-to-end assertions unless strictly needed (belongs in e2e).

**Why:** verifies composition without the cost and brittleness of full workflow harnesses.

---

#### `tests/e2e/`

**Role:** end-to-end validation of user-facing workflows (CLI-level).

**Allowed:**

* CLI invocations and workflow-level assertions (exit codes, emitted artifacts, stdout/stderr shape).
* Minimal scenario coverage reflecting real usage.

**Prohibited:**

* Deep duplication of unit/integration assertions.

**Why:** protects the UX contract while keeping expensive tests small and stable.

---

#### `tests/property/`

**Role:** property-based tests validating invariants across broad input spaces.

**Allowed:**

* Invariants and round-trip properties (normalization, ordering/determinism, encode/decode where applicable).

**Prohibited:**

* Scenario-style workflows (belongs in integration/e2e).

**Why:** systematically explores edge cases and enforces invariants example tests can miss.

---

#### `tests/performance/`

**Role:** performance characterization and regression detection.

**Allowed:**

* Benchmarks for critical pathways (scoping, rendering, aggregation).
* Tests runnable separately from default CI when needed.

**Prohibited:**

* Performance assertions embedded in unit/integration suites.

**Why:** performance is environment-sensitive and should be isolated.

---

#### `tests/fixtures/` (data artifacts only)

**Role:** shared test **data artifacts** used across suites.

**Allowed:**

* Static input data (sample repos/trees, configs).
* Captured/stubbed tool outputs as files (not code).
* Golden files under `tests/fixtures/snapshots/` only.

**Prohibited:**

* Python helper modules or builder/factory code.
* Runtime library code imported by `src/ratchetr/*`.

**Rules:**

* Fixtures are always placed in `tests/fixtures/`.
* Golden files belong in `tests/fixtures/snapshots/` (canonical snapshot location).

**Why:** centralizing data artifacts avoids drift and keeps review/update processes predictable.

---

#### `tests/helpers/` (test code utilities only)

**Role:** shared test **code utilities** used across suites.

**Allowed:**

* Builders/factories for creating domain objects.
* Fake implementations (e.g., fake runners, in-memory stores) used to isolate units.
* Assertion helpers used for consistent, readable checks.

**Prohibited:**

* Being imported by runtime code under `src/ratchetr/`.
* Re-implementing production logic rather than faking at the boundary.

**Why:** separating test code utilities from data artifacts keeps the test taxonomy clean and prevents “fixtures” from becoming a mixed-purpose bucket.

#### `conftest.py`

* Suite-level `conftest.py` is permitted; keep it thin and avoid cross-suite coupling.

## Consequences

### Positive

* Clear, enforceable placement rules reduce structural drift and import cycles.
* Deliberate curation of shared code (`common/`) supports DRY without “utils sprawl.”
* Explicit boundary-package requirement prevents external-representation concerns from leaking into runtime layers.
* Tests become self-placing and easier to maintain as the repo grows.

### Negative / Tradeoffs

* Requires periodic refactors to keep modules in correct layers as features evolve.
* Curated sharing requires discipline and occasional “promote/demote” decisions.

## Links

* `tests/README.md` (test suite intent and pyramid layout)
* Existing ADRs (policy, CLI semantics, engines) — separate scope from taxonomy ADRs
* Repository tree: `src/ratchetr/` (package taxonomy), `tests/` (suite taxonomy)

---
