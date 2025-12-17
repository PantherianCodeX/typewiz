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

**Chosen Option:** Adopt **repo-wide naming conventions** with mandatory suffix rules for key object families, explicit provenance fields for records that require provenance, provenance-aware naming for scope controls, and strict boundary rules for external casing/keys.

This is intentionally strict pre-release: rename churn is cheaper now than post-release.

---

## Naming Principles

1. **Internal default is snake_case** (fields, locals, parameters, internal dict keys).
2. **External contracts are explicit:** CLI flags, env vars, config keys, and persisted artifacts may choose different naming, but translation must be deliberate and isolated.
3. **Names encode lifecycle stage** where applicable: input intent vs resolved/canonicalized values vs executable plans vs results vs persisted artifacts.
4. **Avoid ambiguous nouns** unless qualified by a suffix/prefix that signals intent.
5. **Prefer one canonical name per concept** and refactor legacy names opportunistically.
6. **American English only:** identifiers use `normalize`, `normalized`, `normalization` (not `normalise`, etc.). When a term becomes part of a cross-feature concept, it must be spelled consistently everywhere.

---

## Terminology

Ratchetr uses the following terms as **distinct concepts**, not synonyms:

* **Plugin** — a loadable/registrable extension unit. Plugins may provide one or more engines. (“Packaging and discovery.”)
* **Engine** — a runnable capability that produces ratchetr diagnostics for a target language/toolchain. (“The thing that runs.”)
* **Tool** — an external analyzer invoked by an engine (e.g., pyright, mypy, ruff). (“The third-party program/library and invocation details.”)

ASCII mental model:

```text
plugin (extension package)
  └─ provides → engine (runnable capability)
        └─ invokes → tool (external analyzer)
```

**Rule:** do not use `plugin`, `engine`, and `tool` interchangeably.

---

## Provenance fields

Some records must carry provenance so downstream consumers can reliably answer “where did this come from?” without inference.

* `origin` (mandatory when provenance is relevant) — the **ultimate source** at the point the record entered ratchetr’s canonical stream.

  * Values MUST be low-cardinality and stable (e.g., `engine` | `ratchetr`).
* `producer` (optional) — the component that **materialized/emitted** the record in its current canonical form (“last writer” / materializer).

  * Values SHOULD remain controlled and meaningful (e.g., `engine`, `cache`, `ratchetr`), but `producer` MUST NOT replace `origin`.

Rules:

1. `origin` is assigned at first creation of the canonical record and MUST be preserved by downstream transforms.
2. `producer` MAY change when a record is re-materialized (rehydrated, adapted, re-emitted).
3. Do not invent synonyms (`source`, `emitter`) unless a distinct meaning is required and documented.

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
* `*Result` — runtime outcome of executing a unit (status, timings, counts, failures).
* `*Artifact` — persisted output (files, indexes, caches) with stable semantics.
* `*Summary` — aggregated structure for rollups.
* `*Report` — formatted view (text/JSON/HTML) derived from results/summaries/artifacts.

Diagnostics and lifecycle records:

* `*Diagnostic` — canonical “reportable condition” record.

  * When a `Diagnostic` carries provenance, it uses the global `origin` / `producer` fields.
* `*Event` — structured lifecycle/telemetry signal (timeline/log stream). Events are not a substitute for diagnostics.

Structured non-exception outcome records:

* `*Issue` — non-exception structured record for notable conditions that are not binary failures.
* `*Failure` — non-exception structured record representing a failed operation/step.
* `*Violation` — non-exception structured record representing a policy/contract breach.

### Special-purpose suffixes

* `*Model` — validation models (framework-agnostic). Do not use for runtime dataclasses.
* `*Payload` — dict-shaped record intended for serialization (internal shape; see adapters for wire casing).
* `*Record` — presentation-friendly row/view representation.
* `*Entry` — an element within a collection (store/list/map).
* `*Overrides` — optional override bundle (not effective state).
* `*DebugBundle` / `*TroubleshootingBundle` — a bundle of diagnostics and related context (never a single diagnostic record).
* `*Check` — predicate/evaluator helper.

### Prefix rules

* `Effective*` — final, merged choices (post-precedence).
* `Canonical*` — stable identity is the point (e.g., canonical path key).

### Avoid ambiguous nouns

Avoid generic names without taxonomy signals: `Data`, `Info`, `State`, `Details`, `Options`, and unqualified `Spec`.

### Collections

Prefer semantic plurals:

* `EngineInvocations`, `ScopeTargets`, `OutputTargets`, `CacheEntries`, `RuleCounts`.

---

## Diagnostics and tool-native shapes

`Diagnostic` is ratchetr’s canonical record for reportable conditions, regardless of whether the underlying information came from an engine/tool or from ratchetr itself.

To avoid terminology collisions with external analyzers:

* Raw tool/engine-native shapes MUST NOT be named `Diagnostic`.
* Use `ToolDiagnostic` (preferred) or `ToolMessage` for tool-native payloads prior to canonicalization.
* If an engine needs a domain-local intermediate type, qualify it (e.g., `PyrightToolDiagnostic`) and translate into the canonical `Diagnostic`.

Rule of thumb:

```text
reportable condition → Diagnostic
lifecycle/timeline   → Event
```

---

## Error suffix reservation

* Exception types MUST end in `Error` (e.g., `ConfigError`, `ManifestVersionError`).
* Non-exception records MUST NOT use the `Error` suffix. Use `*Issue`, `*Failure`, `*Violation`, `*Diagnostic`, `*Result`, etc.

---

## Naming for Scope Controls

To prevent ambiguity between “what the user asked for”, “engine overrides”, and “the merged outcome”, scope naming is provenance-aware:

* Project-level baseline (after precedence): `default_include`, `default_exclude`
* Per-engine override controls: `engine_include`, `engine_exclude`
* Computed merged lists used for execution: `effective_include`, `effective_exclude`

Rule: unqualified `include`/`exclude` are reserved for external UX (CLI/env/config) or for clearly engine-local structures where provenance cannot be confused.

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

* Engine identifiers MUST be lowercase and stable (e.g., `pyright`, `mypy`).
* Profiles are user-facing tokens; they SHOULD be lowercase and human-readable (e.g., `baseline`, `strict`).
* Do not encode implementation detail in identifiers (avoid `pyright_v1`, `mypy_new`); versioning is captured via config or tool version metadata.

### Units and quantities

Use explicit unit suffixes for numeric values:

* `_ms`, `_seconds`, `_bytes`, `_count` (internal snake_case)
* Wire fields may use unit suffixes but MUST remain in adapters if camelCase is required.

### Normalization naming

When code performs canonicalization/normalization steps:

* Prefer verb form `normalize_*` for functions (e.g., `normalize_patterns`, `normalize_paths`).
* Prefer adjective form `normalized_*` for derived values (e.g., `normalized_root`, `normalized_patterns`).
* Prefer noun form `normalization_*` for policies/settings describing the rules (e.g., `normalization_policy`).

---

## Module and File Naming

### Standard filenames (preferred)

Prefer these canonical filenames when applicable:

* `models.py` — validation models (`*Model`).
* `typed.py` — internal payload types (`*Payload`, `*Entry`, etc.) in **snake_case**.
* `types.py` — runtime dataclasses/enums/types local to the domain.
* `type_aliases.py` — type aliases and NewTypes.
* `exceptions.py` — domain exceptions.
* `constants.py` — stable constants.
* `policies.py` — policy objects and evaluators.
* `execution.py` — execution wiring for a domain (invocations, runners).
* `loader.py` / `builder.py` — load/build steps when those concepts are real in the domain.
* `views.py` — presentation-only view types used by renderers.

### Constants, paths, and filesystem identifiers

Names that relate to the filesystem MUST communicate whether they represent a **basename**, a **directory**, or a **path**.

Suffix rules (mandatory):

* `*_FILENAME` — basename only (no separators). Example: `DEFAULT_MANIFEST_FILENAME = "manifest.json"`.
* `*_DIRNAME` — directory name only (no separators). Example: `DEFAULT_TOOL_HOME_DIRNAME = ".ratchetr"`.
* `*_PATH` — a path value (relative or absolute). Example: `DEFAULT_RATCHET_PATH = Path(".ratchetr/ratchet.json")`.
* `*_DIR` — a directory path (a `Path` expected to be a directory location).

Rule: do not use `*_FILENAME` for values that may contain a parent directory, and do not use `*_PATH` for basename-only constants.

Single source of truth (mandatory):

* Canonical artifact filenames and candidate-name lists MUST be defined once (prefer `config/constants.py` for basenames and `_infra/paths.py` for discovery candidates) and imported everywhere.
* Duplicated candidate-name lists are prohibited.

### Avoid generic “utils/helpers” naming

Avoid catch-all module names such as `utils.py`, `helpers.py`, or pervasive `*_utils.py` / `*_helpers.py`. Prefer concrete nouns (`paths.py`, `json.py`, `overrides.py`, `logging.py`, `rendering.py`).

If a bucket is unavoidable, it must have a documented, enforceable meaning:

* `utils/` contains primitives (small, deterministic building blocks; minimal coupling).
* `helpers/` contains glue (convenience wrappers, orchestration, formatting; often I/O).

Rule: `_infra/` should not be a dumping ground for glue. Prefer eliminating buckets by using concrete modules at `_infra/` root. If a bucket is still required in `_infra/`, it should generally be `utils/` (primitives).

---

## Adapters and Wire/Persisted Mappings

`adapters/` is the only approved location for casing transformations and wire/persisted key maps.

Recommended structure:

* `adapters/<artifact>/` for artifact-specific translation (e.g., `adapters/manifest/`, `adapters/summary/`)
* `adapters/<artifact>/wire.py` (or `to_wire.py` / `from_wire.py`) to make translation intent explicit

Rule: feature packages may define internal `*Payload`/TypedDict shapes, but they must remain **snake_case** unless adapter-owned.

---

## External Contract Naming

### CLI flags

* Use kebab-case: `--save-as`, `--dry-run`, `--include`, `--exclude`.
* Avoid synonyms for the same concept across commands.

### Environment variables

* Use `RATCHETR_` prefix.
* Use uppercase snake-case.
* Names describe the **user-facing concept**, not internal implementation detail.

Canonical variables:

* `RATCHETR_CONFIG` — config file override (explicit path).
* `RATCHETR_ROOT` — repository root override.
* `RATCHETR_DIR` — tool home directory override (e.g., `.ratchetr/`).
* `RATCHETR_INCLUDE` — include selectors/targets.
* `RATCHETR_EXCLUDE` — exclude selectors/targets.
* `RATCHETR_MANIFEST` — manifest output file override (explicit path).
* `RATCHETR_CACHE_DIR` — cache directory override (explicit path).
* `RATCHETR_LOG_DIR` — log directory override (explicit path).

**Rules:**

* Internal constant names for env vars MUST use a clear suffix (e.g., `*_ENV`).
* List-valued env vars MUST be encoded as a JSON array of strings (e.g., ["src", "tests"]), not comma-separated strings. Support for comma-separated should be a roadmap item.
* The variable name should still communicate plurality/collection intent where possible, except where matching/mirroring external schema overrides.

### Configuration file names

Canonical filenames:

* Project config: `ratchetr.toml` or `.ratchetr.toml` (also allow `pyproject.toml` under `[tool.ratchetr]` when supported @ROADMAP).
* Directory overrides: `ratchetr.dir.toml` or `.ratchetrdir.toml` (located in the user-scoped directory).
* Default tool home directory: `.ratchetr/` (stores cache/logs/artifacts unless configured).

### Artifact filenames (defaults)

Defaults must remain stable to keep automation predictable:

* Manifest: `manifest.json`
* Dashboard HTML: `dashboard.html`
* Cache directory: `.cache/` (under tool home)
* Log directory: `logs/` (under tool home)

Legacy artifact filenames are not supported.

---

## How to Name a New Object

When introducing a new type/module/field:

1. Identify the boundary: internal runtime vs external contract vs wire/persisted.
2. Choose lifecycle stage: token/spec/resolved/policy/plan/invocation/result/artifact/summary/report/diagnostic/event/issue/failure/violation.
3. Choose the container:

   * validation model (`*Model` in `models.py`)
   * runtime type (`types.py`)
   * internal payload (`*Payload` in `typed.py`)
   * wire mapping (adapters)
4. Apply provenance naming: use `origin` and `producer` when provenance is relevant.
5. Avoid ambiguous nouns; prefer names that communicate what makes the thing distinct.
6. Prefer existing vocabulary over inventing near-synonyms.
7. Ensure the module name matches the dominant abstraction (avoid `*_utils.py` catch-alls).

---

## Consequences

### Positive

* Names communicate intent and lifecycle stage reliably.
* Boundary casing rules remain mechanically enforceable.
* Provenance-aware scope naming reduces confusion and refactor churn.
* External contracts (CLI/config/env) are easier to document and keep consistent.

### Negative / Tradeoffs

* Some pre-release rename churn is expected and intentional.
* Requires discipline and ongoing review to keep naming aligned.
* Adapter introduction may require short-term duplication during migrations.

---

## Implementation Notes

1. Add lightweight structural checks (or lint rules) for:

   * camelCase outside adapters
   * prohibited catch-all module naming
   * reserved suffix misuse (`*Model`, `*Payload`, `*Error`, etc.)
2. Ensure docs/examples use the external contract naming consistently.
3. Prefer staged migrations: introduce adapters and translate to stable internal snake_case; retire legacy persisted shapes/keys when feasible.

---

## Appendix A: Known Violations (inventory)

This appendix is a non-exhaustive inventory intended to drive cleanup work. It should be updated or removed once the repo converges.

(Inventory intentionally omitted here; track in code review notes or an issue tracker to avoid making ADR-0005 depend on a particular snapshot.)

---

## Links

* ADR-0001: Include/Exclude and scoping semantics
* ADR-0003: Policy boundaries
* ADR-0004: Repository taxonomy and directory structure
