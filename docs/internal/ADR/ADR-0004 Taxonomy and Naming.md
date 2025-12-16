# ADR-0004: Taxonomy and Naming Conventions

**Status:** Accepted
**Date:** 2025-12-15
**Owners:** Ratchetr maintainers
**Scope:** Defines a repo-wide taxonomy for types and naming conventions. Establishes a consistent vocabulary for “what a thing is” (inputs, resolved values, executable blueprints, results, persisted artifacts, diagnostics) so new features and refactors remain cohesive, predictable, and easy to reason about across the entire codebase.

---

## 1. Context

Ratchetr is evolving into a multi-command, multi-engine system with a growing set of domain objects spanning configuration, path resolution, scoping, engine execution, caching, and artifact generation. The codebase already contains distinct “families” of types (validation models, `TypedDict` payload shapes, runtime dataclasses, records, results), but naming and placement are not yet uniformly enforced.

A lightweight but strict taxonomy is needed to:

* make intent obvious from names alone
* guide where types belong and how they compose
* prevent conceptual drift (mixing raw inputs, resolved values, runtime state, and persisted artifacts)
* reduce refactor churn by stabilizing semantics early (pre-release)
* maintain clear boundaries between internal domain objects and external representations

This ADR defines that taxonomy without prescribing specific workflows or layering mechanics (covered elsewhere).

---

## 2. Decision Summary

Ratchetr will:

1. Adopt a small, stable **type taxonomy** and enforce it via naming conventions.
2. Require that each type’s name clearly communicates:

   * whether it represents **input intent**, a **resolved value**, an **executable blueprint**, a **runtime outcome**, a **persisted artifact**, or a **diagnostic event**.
3. Distinguish **schema/validation** types from **runtime** types:

   * `TypedDict` shapes for serialized artifacts
   * Pydantic `*Model` for validation at boundaries
   * runtime dataclasses/enums for internal logic
4. Rename project baseline scope fields to provenance-aware names:

   * `include_paths` / `exclude_paths` → **`default_include` / `default_exclude`**
   * engine overrides: **`engine_include` / `engine_exclude`**
   * computed merged values: **`effective_include` / `effective_exclude`**
5. Standardize suffixes and rules for composition so types remain cohesive and non-overlapping.
6. Restrict any external schema casing requirements (e.g., camelCase keys) to a dedicated boundary package: **`ratchetr/adapters/`**.
7. Separate **external UX terminology** (CLI/env/config) from **internal field naming** only where necessary for clarity and uniqueness.

---

## 3. Type Taxonomy

Each type must fit **one** category. A type should fit one category; if it doesn’t, it is likely doing too much and should be decomposed.

### 3.1 Token

A *Token* is raw user-facing text or CLI/environment “token” that has not been interpreted.

* Examples: raw selector strings, raw output target strings, raw “format:path” segments.
* Naming: `*Token`, `*TokenList`, `Token*`.

**Rule:** Token types are not validated beyond basic shape (string/non-empty), and are not OS/path-resolved.

---

### 3.2 Spec

A *Spec* expresses user intent in structured form, but is not fully resolved.

* Contains tokens plus parsed flags/options.
* May contain “optional” fields that will be filled by resolution rules later.
* Naming: `*Spec`.

**Rule:** Specs do not contain derived paths, precedence outcomes, or computed defaults that require discovery.

---

### 3.3 Config

A *Config* is persisted configuration state loaded from config sources.

* Naming: `*Config`, `*ConfigModel` (when explicitly a validation/serialization model).

**Rule:** Config types represent what is stored and loaded. They do not embed runtime or CLI state.

---

### 3.4 Context

A *Context* represents runtime environment facts necessary for consistent interpretation.

* Examples: working directory, resolved root, resolved tool-home, active config path, environment snapshot (only if needed).
* Naming: `*Context`.

**Rule:** Context types are facts and references, not decisions. If it encodes “what should happen,” it is not a Context.

---

### 3.5 Resolved

A *Resolved* type is the interpreted, canonical form of something that started as a token/spec/config.

* Examples: resolved output destinations, resolved scope bases, normalized paths (absolute + canonical identity fields).
* Naming: `Resolved*` or `*Resolved`.

**Rule:** Resolved types contain fully interpreted values and may include provenance (source attribution). They are not executable blueprints.

---

### 3.6 Policy

A *Policy* represents rules/constraints/settings that govern how resolution or planning should behave.

* Naming: `*Policy`.

**Rule:** Policy types describe “how to decide,” not “what will run.” They are not plans.

---

### 3.7 Plan

A *Plan* is an executable blueprint that can be carried out without reinterpretation.

* Examples: engine invocation plan, artifact emission plan, ordered worklists.
* Naming: `*Plan`.

**Rule:** Plans are concrete and complete: execution should not need to guess missing fields.

---

### 3.8 Invocation / Task

An *Invocation* (or *Task*) is the smallest unit of executable work.

* Examples: “run engine X with inputs Y,” “emit dashboard file Z.”
* Naming: `*Invocation` (preferred for command/tool execution), `*Task` (preferred for internal work units).

**Rule:** Invocation/Task types must be directly executable and should reference the plan data needed to do so.

---

### 3.9 Result

A *Result* is the output of executing one unit (invocation/task).

* Examples: per-engine run result, persistence write result, cache save result.
* Naming: `*Result`.

**Rule:** Results contain runtime outcomes (exit status, timings, counts, errors), not configuration or intent.

---

### 3.10 Artifact

An *Artifact* is a persisted output or a persisted on-disk state object (manifest, dashboard, cache index, logs).

* Naming: `*Artifact` for conceptual outputs; `*Record` or `*File` where specificity matters.

**Rule:** Artifacts are serializable and stable. They should not embed runtime-only process state.

---

### 3.11 Summary / Report

A *Summary* is an aggregate data structure used for presentation or rollups. A *Report* is a formatted view (text/JSON/HTML) of results/artifacts.

* Naming: `*Summary`, `*Report`.

**Rule:** Reports are derived views; they should not be treated as canonical persisted state unless explicitly defined as an Artifact.

---

### 3.12 Finding / Event

A *Finding* (or *Event*) is a structured diagnostic emitted during resolution, planning, or execution.

* Naming: `*Finding` (preferred for “something noteworthy happened”), `*Event` (preferred for timeline/log streams).

**Rule:** Findings/Events must be structured (stable `code`, severity, payload). Avoid unstructured “notes: list[str]”.

---

## 4. Naming Conventions and Suffix Rules

### 4.1 Suffix rules (mandatory)

* `*Token`, `*Spec`, `*Config`, `*Context`, `Resolved*` / `*Resolved`, `*Policy`, `*Plan`, `*Invocation` / `*Task`, `*Result`, `*Artifact`, `*Summary`, `*Report`, `*Finding` / `*Event`.
* `*Model` (Pydantic validation)
* `*Payload` (wire/persisted dict intended for serialization)
* `*Record` (presentation-friendly row/view)
* `*Overrides` (optional override bundles; not effective state)
* `Resolved*` / `Loaded*` (post-processing or loaded-with-metadata)
* `*Diagnostics` (system troubleshooting bundle; avoid collision with tool `Diagnostic`)
* `*Entry` (stored item in a collection/store)
* `*Result` (operation outcome)
* `*Check` (predicate/evaluator helper)

### 4.2 "Effective" and "Canonical" Prefixes

* Use `Effective*` for “final merged choice” (e.g., merged config view).
* Use `Canonical*` only when a stable identity is the point (e.g., canonical path key).

### 4.3 Avoid ambiguous nouns

Avoid generic names without taxonomy signals: `Data`, `Info`, `State`, `Payload` (unless prefixed/suffixed), `Spec` (unless category-qualified, e.g., `EngineOptionsSpec`).

### 4.4 Collection naming

Prefer semantic plurals: `EngineInvocations`, `ScopeTargets`, `OutputTargets`, `CacheEntries`.

---

## 5. Provenance-aware scope naming

To avoid ambiguity between project defaults, engine overrides, and computed merged values:

1. **Project defaults**:

   * `default_include`, `default_exclude`
   * Meaning: baseline scope lists for the run after precedence resolution (CLI/env/config/defaults).

2. **Engine overrides**:

   * `engine_include`, `engine_exclude`
   * Meaning: per-engine scope controls applied during engine planning.

3. **Computed effective lists**:

   * `effective_include`, `effective_exclude`
   * Meaning: post-merge normalized lists used to execute and/or filter diagnostics.

**Rule:** Unqualified `include`/`exclude` and similar names are reserved for external UX (CLI/env/config) and should not be used for internal fields unless the object is unambiguously engine-local and provenance cannot be confused.

---

## 6. Composition Rules

1. A `*Plan` composes `Resolved*` values and `*Policy` values; it should not contain `*Token` or `*Spec`.
2. A `*Result` may reference the `*Invocation` it came from (or a stable identifier), but should not embed the full `*Plan` unless required for persistence/debugging.
3. A `*Report` consumes `*Result`, `*Summary`, and/or `*Artifact`, not raw `*Spec`.
4. A `*Finding` can occur at any stage, but its **stage** must be explicit in naming or fields if it impacts interpretation.

---

## 7. Boundary layer: external schema casing is adapter-only

Ratchetr standardizes on **snake_case** for internal Python identifiers (types, fields, locals, parameters, internal dict keys). Any external representation requirements (including camelCase keys) are handled exclusively in the boundary package:

* **Package:** `ratchetr/adapters/`
* Purpose: translate between internal domain objects and external wire/persisted forms.

**Rules:**

1. camelCase keys and vendor field names are permitted only under `ratchetr/adapters/`.
2. Internal domain types remain snake_case; conversion occurs via explicit `to_wire/from_wire` (or equivalent) adapters and/or model alias configuration placed in adapters.
3. Lint/style exceptions related to casing may be scoped to `ratchetr/adapters/` only.

This boundary remains intentionally narrow in this ADR: it exists to keep internal naming consistent and mechanically enforceable while allowing external schema compatibility.

---

You’re right. In my last rewrite I only supplied deltas for **8.5 / 8.11 / 8.13** and did not include (or restate) the **original 8.1–8.3 guidance**, nor the rest of the placement taxonomy that makes the section actually actionable.

What was missing relative to a complete “Module placement guidance” section:

* 8.1 Canonical schema shapes (TypedDict placement)
* 8.2 Validation models (Pydantic `*Model` placement)
* 8.3 Runtime domain objects (dataclasses/enums placement)
* 8.4 Adapters (boundary translation placement)
* The repo-wide placement rules that make those lines usable in practice (package-root shims, `_internal`, `_internal/utils`, `core`, `config`, feature packages, `services`, `cli`, `common`, and the “where does this helper go?” decision tree)

Below is a **full replacement** for **Section 8** (all subsections), incorporating your requested corrections (notably the `compat/` stance and DRY guidance) while retaining the original 8.1–8.3 content and expanding it into effective direction.

---

## 8. Module placement guidance

### 8.1 Canonical schema shapes

* `TypedDict` for serialized artifacts belongs in the subdomain that owns the artifact:

  * feature-local: `*/typed.py` (preferred)
  * core-level: `core/*_types.py` only for truly cross-cutting primitives shared by multiple subdomains

**Rule:** If a schema shape is primarily consumed by one feature (manifest, dashboard, readiness, ratchet), it must be defined within that feature package. Cross-feature placement in `core/` is the exception, not the default.

---

### 8.2 Validation models

* Pydantic validation types must be explicitly named and scoped:

  * configuration models: `config/models.py`
  * artifact validation models: `<feature>/models.py` (e.g., `manifest/models.py`)
  * boundary/wire-specific models: `adapters/...` (only when the model exists to represent an external/wire schema)

**Rules:**

1. Pydantic models must end in `*Model`.
2. Validation belongs at the boundary where data enters ratchetr (config ingestion, artifact ingestion, wire decoding). Runtime code should consume validated runtime dataclasses and enums rather than re-validating ad hoc.

---

### 8.3 Runtime domain objects

* Runtime dataclasses/enums belong in the domain packages that own the behavior:

  * foundational cross-cutting vocabulary: `core/`
  * engine interface and engine-local runtime types: `engines/`
  * feature domain logic: feature packages (e.g., `manifest/`, `dashboard/`, `readiness/`, `ratchet/`, `audit/`)
  * orchestration-only runtime types (when needed): `services/`
  * CLI-only runtime types: `cli/`

**Rule:** Runtime types must not be placed in boundary packages (`adapters/`) unless they exist solely to represent a wire format.

---

### 8.4 Package-root shims and public façade modules

Package-root modules (e.g., `ratchetr.paths`, `ratchetr.cache`, `ratchetr.audit.api`) are reserved for **stable public shims/façades** and must remain thin.

**Allowed in shims/façades:**

* explicit re-exports (`__all__`)
* small coordination glue to expose a stable API surface

**Prohibited in shims/façades:**

* non-trivial business logic
* hidden policy decisions and precedence
* deep helper implementations

**Rule:** If a capability is intended to be reusable across the repo (or by embedders), expose it via a package-root façade. Implementation belongs in a private module (feature-local or `_internal/`), not in the shim.

---

### 8.5 `_internal/` and `_internal/utils/`

`_internal/` is a **private infrastructure** layer. It is not a general dumping ground.

**`_internal/utils/` is for:**

* low-level, dependency-minimized utilities (process invocation, file locks, basic path helpers, version helpers)
* code safe to import widely without pulling in feature packages

**`_internal/` is for:**

* private implementations behind public shims/façades
* infrastructure implementations (e.g., caching primitives, persistence plumbing, shared resolution primitives) that are not feature domain logic

**Prohibited in `_internal/`:**

* feature/domain logic (audit semantics, manifest semantics, engine behavior)
* CLI parsing and presentation
* wire-format concerns (those belong in `adapters/`)

**Import rule:** Feature and CLI code should prefer public shims/façades over importing `ratchetr._internal.*` directly.

---

### 8.6 `compat/`

`compat/` is reserved for **cross-version and cross-platform compatibility shims** and is the **single import source of truth** for backports used across the codebase.

**Intended usage (required pattern):**

* When a module needs a language or platform backport, it imports it from `ratchetr.compat.*`.
* Modules must not re-implement compatibility logic using local `try/except ImportError` patterns except within `compat/` itself (or in narrowly justified boundary glue).

**Rules:**

1. **Leaf-like dependency posture:** `compat/` must not import from ratchetr feature packages (`audit/`, `engines/`, `manifest/`, `services/`, `cli/`) and should avoid importing from anything beyond stdlib and narrow compatibility dependencies (e.g., `typing_extensions`).
2. **Compatibility only (no domain):** `compat/` must not contain project/domain semantics. If a helper is “generically useful” but not compatibility, it belongs in `_internal/utils/`, `common/`, or a feature package.
3. **Stable behavior:** abstractions defined in `compat/` define the contract consumed by the rest of the codebase.
4. **Upgrade path:** raising minimum Python versions should primarily reduce `compat/`, not trigger sweeping refactors.

---

### 8.7 `core/`

`core/` contains foundational, cross-feature vocabulary:

* shared enums and categories (severity/status/readiness)
* stable `NewType` and type aliases
* small, stable shared domain primitives

**Rules:**

* Keep `core/` dependency-light and low churn.
* Prefer feature-local types unless they are truly cross-cutting.

---

### 8.8 `config/`

`config/` owns configuration ingestion and validation:

* discovery/selection of configuration sources (where applicable)
* config parsing and validation models (`*Model`)
* conversion into internal runtime config objects
* configuration defaults and schema versioning (when applicable)

**Rule:** Config discovery/validation must not be duplicated in CLI/services/features. Those layers consume the resolved config outputs.

---

### 8.9 Feature packages (domain logic)

Feature packages own their domain logic and feature-local schemas/models:

* `audit/`: audit domain logic (planning inputs, audit-specific structures)
* `manifest/`: manifest typed shapes and semantics
* `dashboard/`: summary shaping and renderers
* `readiness/`: readiness computation and view-model generation
* `ratchet/`: ratcheting rules and baseline logic
* `engines/`: engine interfaces, registry, builtin implementations

**Rules:**

* Keep helpers feature-local by default.
* Promote cross-feature helpers only when reuse is proven and semantics are stable.

---

### 8.10 `services/`

`services/` is the orchestration/application layer:

* composes feature logic into cohesive operations
* owns side-effect boundaries (file I/O, persistence orchestration, dry-run write gating)
* provides stable call surfaces for CLI and embedding callers

**Rule:** Services coordinate; they do not redefine feature semantics.

---

### 8.11 `cli/`

`cli/` owns user interaction:

* parsing flags/positionals and shaping specs
* formatting and presentation
* exit codes and UX-level validation messages

**Rule:** CLI must not contain domain logic beyond shaping inputs and calling services.

---

### 8.12 `common/`

`common/` is reserved for **small, stable, curated cross-feature helpers** that are shared across multiple feature packages and are not appropriate for `_internal/utils/`.

**DRY guidance (explicit):**

* Ratchetr prefers to keep the codebase DRY. When identical logic appears across modules and the semantics are stable, it should be refactored into a shared helper rather than duplicated.
* Shared helpers must remain curated; `common/` must not become a generic “misc utils” bucket.

**Rules:**

1. `common/` remains small and curated; additions must be demonstrably cross-feature and stable.
2. If a helper gains feature assumptions, move it into the owning feature package (or split it).
3. `common/` must not introduce dependency cycles; it may depend on `compat/` and `core/`, but must not depend on `cli/`.

---

### 8.13 `adapters/` (boundary translations)

`adapters/` is the explicit boundary layer for external representations:

* wire/persisted JSON encoding/decoding
* schema mapping, aliasing, casing transforms (camelCase)
* tool/vendor field mapping where external key spaces must be preserved

**Rules:**

1. Non-snake_case identifiers and external key names are permitted **only** under `adapters/`.
2. Feature packages produce canonical internal structures; adapters translate them for external consumption.
3. Adapter code must not become a home for domain logic.

---

### 8.14 Helper placement rules (“where does this helper go?”)

When adding or refactoring a helper, choose placement using the following ordered rules. These rules explicitly support DRY while preventing “misc utils” sprawl.

1. **Feature-private helper (default):** place it in the owning feature package.
2. **Refactor duplication when semantics are stable (DRY rule):** identical logic duplicated across modules should be refactored into a shared helper once semantics are stable and clearly described.
3. **Cross-feature, domain-aware helper:** if there is no single natural owner, place it in `common/`.
4. **Infrastructure / dependency-light helper:** if it must remain safe to import widely and dependency-light, place it in `_internal/utils/`.
5. **Single-feature ownership with reuse:** if one feature owns semantics but others reuse it, keep it in the owning feature and expose via an explicit public shim/façade if needed.
6. **Boundary-only transformation helper:** if it translates to/from external schemas (including casing), it belongs in `adapters/`.

**Prohibited patterns:**

* global `utils.py` / `helpers.py` catch-alls for unrelated functions
* “small therefore shared” without proven reuse and stable semantics

---

## 9. Consequences

**Positive**:

* Names communicate category and intent reliably.
* Provenance-aware scope naming reduces confusion and refactor churn.
* External schema requirements are isolated and enforceable.
* Refactors become safer because semantics are stable and testable by category.
* Future ADRs and refactors have a stable vocabulary foundation.
* Documentation and ADRs can reference a consistent vocabulary.

**Tradeoffs**:

* Some pre-release rename churn (intentional; cheaper now than post-release).
* Requires discipline and periodic cleanup to keep legacy types aligned.
* Some legacy types may need to be decomposed to fit a single category cleanly.

---

## 10. Implementation Notes

1. Rename baseline scope fields:

   * `include_paths`/`exclude_paths` → `default_include`/`default_exclude`
   * Ensure internal merge outputs use `effective_*`
   * Ensure engine wiring uses `engine_*`

2. Rename selection aggregates currently named as plans (where applicable):

   * e.g., consider renaming output selection objects away from `*Plan` if they are not execution-equivalence plans.

3. Introduce `ratchetr/adapters/` and move any external casing / wire mapping logic into it.

---

## 11. Test Strategy

* Unit tests ensure renamed config/runtime fields map correctly.
* Structural tests or review checklist: new types must conform to taxonomy suffix rules.
* Lint enforcement: casing exceptions scoped to `ratchetr/adapters/` only (no camelCase leakage).

---

## 12. Follow-ups

1. Apply taxonomy consistently in new code; refactor existing types opportunistically.
2. Establish a stable catalog for `*Finding.code` values and severity conventions (separate ADR or appendix).
3. Align future architecture documents (policy/planning/execution layering) to this shared taxonomy.
4. Add lightweight lint/check guidance for naming convention ignores to the adapter/ layer and possibly prefix/suffix enforcement as the code stabilizes.

---
