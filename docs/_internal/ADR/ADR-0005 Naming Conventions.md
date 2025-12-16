# ADR-0005: Naming Conventions

**Status:** Accepted
**Date:** 2025-12-16
**Deciders:** Ratchetr maintainers
**Technical Story:** N/A (repo-wide naming contract)

## Context and Problem Statement

Ratchetr is a multi-command, multi-engine system with a growing set of domain objects spanning configuration ingestion, scoping and selection, engine execution, caching, and artifact generation. As the codebase expands, ambiguous or inconsistent naming becomes one of the fastest ways to introduce design drift, refactor churn, and accidental policy leakage across layers.

We need a repo-wide naming contract that:

* makes intent obvious from names alone
* keeps naming stable and predictable across domains (audit/manifest/dashboard/ratchet/readiness/engines/config)
* clearly separates internal naming from external representations (CLI, config, wire/persisted JSON)
* provides a repeatable procedure for naming new objects and refactors
* is enforceable through reviews, linting, and lightweight structural checks

This ADR scopes **naming only** (types, fields, modules, packages, external contracts). Repository taxonomy and layering rules are governed elsewhere (see ADR-0004).

## Decision Drivers

* **Predictability:** names should be guessable (by humans and tooling).
* **Signal over cleverness:** names should communicate category, lifecycle stage, and ownership.
* **Boundary hygiene:** external schema constraints must not contaminate internal identifiers.
* **Refactor friendliness:** names should reduce churn when modules move or responsibilities split.
* **Cross-domain consistency:** identical concepts should not be spelled differently in different packages.

## Considered Options

1. **Ad hoc naming (status quo):** rely on reviewer judgement; allow local conventions per module.
2. **Domain-local conventions only:** each feature defines its own naming; no repo-wide suffix/prefix rules.
3. **Repo-wide naming conventions with enforced suffix/prefix rules and boundary casing rules** (chosen).

## Decision Outcome

**Chosen Option:** Adopt **repo-wide naming conventions** with mandatory suffix rules for key object families, provenance-aware naming for scope controls, and strict boundary rules for external casing/keys.

This is intentionally strict pre-release: rename churn is cheaper now than post-release.

---

## Naming Principles

1. **Internal default is snake_case** (fields, locals, parameters, internal dict keys).
2. **External contracts are explicit**: CLI flags, env vars, config keys, and JSON schemas may choose different naming, but translation must be deliberate and isolated.
3. **Names encode lifecycle stage** where applicable: input intent vs. resolved/canonicalized values vs. executable plans vs. results vs. persisted artifacts.
4. **Avoid ambiguous nouns** unless qualified by a suffix/prefix that signals intent.
5. **Prefer one canonical name per concept** and refactor legacy names opportunistically.

---

## Type Naming

### Suffix rules (mandatory)

Use these suffixes when the concept exists; do not invent near-synonyms:

* `*Token` — raw, user-facing/uninterpreted inputs (often strings).
* `*Spec` — structured intent (parsed inputs) but not fully resolved.
* `*Config` — persisted configuration state (what is stored/loaded).
* `*Context` — runtime facts necessary for interpretation (environmental facts, not decisions).
* `Resolved*` / `*Resolved` — canonicalized, interpreted values (often with provenance).
* `*Policy` — rules/constraints that govern how decisions are made.
* `*Plan` — executable blueprint (complete enough to run without guessing).
* `*Invocation` / `*Task` — smallest unit of executable work.
* `*Result` — runtime outcome of executing a unit (status, timings, counts, errors).
* `*Artifact` — persisted output (files, indexes, caches) with stable semantics.
* `*Summary` — aggregated structure for rollups.
* `*Report` — formatted view (text/JSON/HTML) derived from results/summaries/artifacts.
* `*Finding` / `*Event` — structured diagnostic emitted during any stage.

Special-purpose suffixes:

* `*Model` — validation models. Do not use for runtime dataclasses.
* `*Payload` — wire/persisted mapping intended for serialization (dict-shaped).
* `*Record` — presentation-friendly row/view representation.
* `*Entry` — an element within a collection (store/list/map).
* `*Overrides` — optional override bundle (not effective state).
* `*Diagnostics` — troubleshooting bundle (avoid collision with engine/tool “Diagnostic” terms).
* `*Check` — predicate/evaluator helper.

### Prefix rules

* Use `Effective*` for final, merged choices (post-precedence).
* Use `Canonical*` only when stable identity is the point (e.g., canonical path key).

### Avoid ambiguous nouns

Avoid generic names without taxonomy signals: `Data`, `Info`, `State`, `Details`, `Options`, `Payload` (unless wire/persisted), and unqualified `Spec`.

### Collections

Prefer semantic plurals:

* `EngineInvocations`, `ScopeTargets`, `OutputTargets`, `CacheEntries`, `RuleCounts`.

---

## Naming for Scope Controls

To prevent ambiguity between “what the user asked for”, “engine overrides”, and “the merged outcome”, scope naming is provenance-aware:

* Project-level baseline (after precedence): `default_include`, `default_exclude`
* Per-engine override controls: `engine_include`, `engine_exclude`
* Computed merged lists used for execution: `effective_include`, `effective_exclude`

**Rule:** Unqualified `include`/`exclude` are reserved for external UX (CLI/env/config) or for clearly engine-local structures where provenance cannot be confused.

When the values are **concrete path lists** (not selector patterns), prefer `*_paths` for internal fields (e.g., `scanned_paths`, `selected_paths`) to signal that these are resolved paths, not selector patterns.

---

## Boundary Casing Rules

Ratchetr standardizes on **snake_case** internally. Any external representation requirements (including camelCase keys or vendor-specific field names) must be handled exclusively via a boundary translation layer (adapters).

Rules:

1. camelCase keys and vendor field names are permitted only in adapters (wire/persisted mappings).
2. Feature packages and core types remain snake_case; conversion occurs via explicit `to_wire`/`from_wire` (or equivalent) adapters and/or model alias configuration placed in adapters.
3. Lint/style exceptions related to casing may be scoped to adapters only.

---

## Identifiers and Tokens

### Engine names and profile names

* Engine identifiers (`EngineName`, `RunnerName`) MUST be lowercase and stable (e.g., `pyright`, `mypy`).
* Profiles are user-facing tokens; they SHOULD be lowercase and human-readable (e.g., `baseline`, `strict`).
* Do not encode implementation detail in identifiers (avoid `pyright_v1`, `mypy_new`); versioning is captured via config or tool version metadata.

### Units and quantities

Use explicit unit suffixes for numeric values:

* `_ms`, `_seconds`, `_bytes`, `_count` (internal snake_case)
* Wire fields may use unit suffixes but MUST remain in adapters if camelCase is required.

---

## Exceptions and Errors

Naming:

* Exceptions MUST end in `Error` (`ManifestVersionError`, `ConfigError`).
* Base exception type SHOULD be `RatchetrError` for domain-level failures; use standard built-ins (e.g., `ValueError`) only for narrow “invalid argument” cases at pure-function boundaries.

Placement:

* Domain exceptions belong in `exceptions.py` within the owning package.
* Infrastructure exceptions belong in the private infrastructure package.

---

## Module and File Naming

### Standard filenames (preferred)

To keep navigation predictable, prefer these canonical filenames when applicable:

* `models.py` — validation models (`*Model`).
* `typed.py` — wire/persisted payload types (`*Payload`, `*Entry`, etc.). If these payloads require camelCase, they MUST live behind adapters.
* `types.py` — runtime dataclasses/enums/types local to the domain.
* `type_aliases.py` — type aliases and NewTypes.
* `exceptions.py` — domain exceptions.
* `constants.py` — stable constants.
* `policies.py` — policy objects and evaluators.
* `execution.py` — execution wiring for a domain (invocations, runners).
* `loader.py` / `builder.py` — load/build steps when those concepts are real in the domain.
* `views.py` — presentation-only view types used by renderers.

### Avoid generic “utils/helpers” naming

Avoid catch-all module names such as `utils.py`, `helpers.py`, or pervasive `*_utils.py` / `*_helpers.py`. In nearly all cases, a concrete noun communicates intent more precisely (e.g., `paths.py`, `json.py`, `overrides.py`, `logging.py`, `rendering.py`).

If a bucket is unavoidable, it must have a documented, enforceable meaning:

* `utils/` contains **primitives**: small, deterministic building blocks that are broadly reusable and minimally coupled (ideally pure functions).
* `helpers/` contains **glue**: convenience wrappers, orchestration, formatting, and layer-specific ergonomics (often I/O and tool wiring).

**Rule:** `_infra/` should not be a dumping ground for glue. Prefer eliminating buckets by using concrete modules at `_infra/` root. If a bucket is still required in `_infra/`, it should generally be `utils/` (primitives), while glue belongs in the consuming layer (`cli/`, `adapters/`, `tests/`) where policy and boundary context are explicit.

Examples (preferred):

* `_infra/paths.py` instead of `_infra/utils/path_utils.py`
* `cli/helpers/options.py` is acceptable (CLI glue), but `core/helpers.py` is not.

---

## Adapters and Wire/Persisted Mappings

`adapters/` is the only approved location for casing transformations and wire/persisted key maps.

Recommended structure:

* `adapters/<artifact>/` for artifact-specific translation (e.g., `adapters/manifest/`, `adapters/summary/`)
* `adapters/<artifact>/wire.py` (or `to_wire.py` / `from_wire.py`) to make the translation intent unambiguous

**Rule:** Feature packages may define `*Payload`/TypedDict shapes, but they must remain **snake_case** unless they are adapter-owned.

---

## External Contract Naming

### CLI flags

* Use kebab-case: `--save-as`, `--dry-run`, `--include`, `--exclude`.
* Avoid synonyms for the same concept across commands.

### Environment variables

* Use `RATCHETR_` prefix.
* Use uppercase snake-case.
* Names describe the user-facing concept, not internal implementation.
  * `RATCHETR_INCLUDE` for include selectors/targets
  * `RATCHETR_ROOT` for repository root override
  * `RATCHETR_DIR` for tool home directory override

### Configuration file names

Canonical filenames:

* Project config: `ratchetr.toml` or `.ratchetr.toml` (also allow `pyproject.toml` under `[tool.ratchetr]` when supported).
* Directory overrides: `ratchetr.dir.toml` or `.ratchetrdir.toml` (located in the directory they scope).
* Default tool home directory: `.ratchetr/` (stores cache/logs/artifacts unless configured).

### Artifact filenames (defaults)

Defaults must remain stable to keep automation predictable:

* Manifest: `manifest.json`
* Dashboard HTML: `dashboard.html`
* Cache directory: `.cache/` (under tool home)
* Log directory: `logs/` (under tool home)

Legacy artifact filenames may be supported for discovery only, and must be treated as compatibility inputs (not the canonical output names).

---

## How to Name a New Object

When introducing a new type/module/field:

1. **Identify the boundary**: internal runtime vs. external contract vs. wire/persisted.
2. **Choose lifecycle stage**: token/spec/resolved/policy/plan/invocation/result/artifact/summary/report/finding.
3. **Choose the container**:
   * validation model (`*Model` in `models.py`)
   * runtime type (`types.py`)
   * wire payload (`*Payload` in adapters; or snake_case in `typed.py` + adapter translations)
4. **Apply provenance naming** if scope-related.
5. **Avoid ambiguous nouns**; prefer names that communicate what makes the thing distinct.
6. **Prefer existing vocabulary** over inventing near-synonyms.
7. **Ensure the module name matches the dominant abstraction** (do not hide domain concepts inside `*_utils.py`).

---

## Consequences

### Positive

* Names communicate intent and lifecycle stage reliably.
* Boundary casing rules remain mechanically enforceable.
* Provenance-aware scope naming reduces confusion and refactor churn.
* External contracts (CLI/config/env) are easier to document and keep consistent.

### Negative / Tradeoffs

* Some pre-release rename churn is expected and intentional.
* Requires discipline and ongoing review to keep legacy names aligned.
* Adapter introduction may require short-term duplication during migrations.

---

## Implementation Notes

1. Add lightweight structural checks (or lint rules) for:
   * camelCase outside adapters
   * prohibited catch-all module naming
   * reserved suffixes (`*Model`, `*Payload`, etc.) misuse
2. Ensure docs and examples use the external contract naming consistently.
3. Prefer staged migrations:
   * introduce adapters and translate to stable internal snake_case
   * keep compatibility readers for legacy persisted shapes
   * remove legacy naming when the ecosystem converges

---

## Appendix A: Known Violations in `ratchetr-0.1.0-dev-5` (inventory)

This appendix is an observed, non-exhaustive inventory intended to drive cleanup work. It should be updated or removed once the repo converges.

### A.1 Boundary casing leakage (camelCase outside adapters)

camelCase TypedDict fields and dict keys exist outside `src/ratchetr/adapters/`, notably:

* `src/ratchetr/core/summary_types.py` (e.g., `severityBreakdown`, `ruleFiles`, `runSummary`)
* `src/ratchetr/manifest/typed.py` (e.g., `severityBreakdown`, `ruleFiles`, `runSummary`)
* `src/ratchetr/manifest/models.py`
* `src/ratchetr/cli/helpers/formatting.py` (e.g., `pluginArgs`, `ruleFiles`)
* `src/ratchetr/dashboard/build.py`
* `src/ratchetr/ratchet/models.py`
* `src/ratchetr/readiness/compute.py`
* `src/ratchetr/readiness/views.py`
* `src/ratchetr/_infra/cache.py`
* `src/ratchetr/common/override_utils.py`
* `src/ratchetr/audit/api.py` (e.g., `engine_error` includes `exitCode`)

**Expected direction:** internal structures are snake_case; adapters own wire/persisted camelCase mappings. `src/ratchetr/adapters/` currently exists but is empty.

---

### A.2 Generic module naming (`utils`, `helpers`, and `*_utils.py`)

Potentially over-generic module names and/or buckets (naming does not communicate intent precisely):

* `src/ratchetr/_internal/collection_utils.py`
* `src/ratchetr/_internal/logging_utils.py`
* `src/ratchetr/common/override_utils.py`

**Why this violates the ADR:** catch-all naming obscures responsibility and encourages “grab-bag” growth.

**Expected direction:** rename to concrete nouns matching the dominant abstraction, for example:

* `collections.py` (or `collection_ops.py` if needed)
* `logging.py` (or `log_format.py` / `log_config.py` if more precise)
* `overrides.py`

**Bucket rule:** avoid `utils.py` / `helpers.py` buckets entirely when feasible. If a bucket is unavoidable, `utils/` must be primitives and `helpers/` must be layer-local glue (preferably not in `_infra/`).

---

## Links

* ADR-0001: Include/Exclude and scoping semantics
* ADR-0003: Policy boundaries
* ADR-0004: Repository taxonomy and directory structure
