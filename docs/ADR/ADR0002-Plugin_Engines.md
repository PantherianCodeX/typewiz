# ADR-0002: Engine Execution Planning, Per-Engine Equivalence, Deterministic Scope Resolution, and Engine Failure Semantics

**Status:** Accepted
**Date:** 2025-12-14
**Owners:** Ratchetr maintainers
**Scope:** How ratchetr resolves scan scope for engine runs, how it plans and deduplicates CURRENT/TARGET executions **per engine**, how it treats built-in vs plugin engines, and how engine failures are represented and surfaced (separate from code diagnostics).

---

## 1. Context

Ratchetr orchestrates multiple engines (built-ins and plugins) to produce diagnostics and dashboards from a single run. The tool must be predictable and automation-friendly:

* Scope selection must be deterministic and consistent with the project’s general precedence rules.
* “CURRENT” and “TARGET” runs must be comparable without introducing special-case heuristics.
* The system must avoid doing redundant work when the effective run inputs are equivalent.
* Engine execution failures must be clearly separated from code diagnostics, without polluting results or inventing tool behaviors.

Historically, implementations tend to drift toward implicit heuristics (e.g., “empty targets means tool decides”), cross-mode differences in invocation shapes, or inconsistent selection logic across commands. This ADR establishes a single, testable contract for engine execution planning and failure semantics.

---

## 2. Decision Summary

Ratchetr will:

1. Use **one scope-resolution algorithm** with a single precedence chain:

   ```text
   CLI positional args > environment variables > config file > default ["."]
   ```

2. Define the only mode distinction as **CLI positional scope participation**:

   * **CURRENT** participates in CLI positional args
   * **TARGET** runs without any CLI positional scope input

3. Plan and deduplicate **per engine** using an explicit, canonicalized `EnginePlan`:

   * For each engine, build `EnginePlan(CURRENT)` and `EnginePlan(TARGET)`
   * If plans are equal after canonicalization, execute **TARGET only** for that engine (TARGET is canonical)

4. Require determinism through canonicalization:

   * Scope targets are normalized, deduplicated, and sorted
   * Equivalence must be robust to ordering differences to avoid “equivalence traps”

5. Treat plugins as **execution-mechanics opaque**:

   * Ratchetr does not assert how a plugin runs its tool (runtime, binary, invocation prefix, etc.)
   * Parity and equivalence are enforced on **inputs ratchetr provides**, not on plugin-internal execution strategy

6. Standardize built-in Python engine invocation (where ratchetr owns execution):

   * Use `sys.executable -m <module>` for built-in Python engines
   * Avoid PATH/script ambiguity

7. Enforce deterministic config selection and recording:

   ```text
   CLI config override > env override > ratchetr config > tool-native discovery
   ```

   Ratchetr records the chosen config path (or “none”) but does not interpret tool config semantics.

8. Classify engine failures separately from diagnostics:

   * Valid JSON output yields diagnostics regardless of exit code
   * Invalid/missing/empty/unparseable output yields a structured `engine_error`
   * stderr content never becomes diagnostics

9. Treat an explicitly empty configured scope (for an engine) as a **configuration error** that deselects the engine:

   * The engine is not executed
   * This is not represented as a run with an empty target list
   * Other engines proceed normally

---

## 3. Detailed Decisions

### 3.1 Canonical scope resolution

Scope is resolved via a single, shared algorithm consistent with ratchetr’s general precedence model.

Precedence:

```text
CLI positional args > environment variables > config file > default ["."]
```

Mode input rule:

* CURRENT supplies `cli_paths` to scope resolution.
* TARGET supplies no CLI positional scope input (i.e., CLI positional args do not participate).

**Rationale:** This eliminates mode-specific heuristics and ensures a uniform mental model. TARGET is “target” because it is not restricted by CLI positional scope input, while still honoring the same environment/config/default sources.

---

### 3.2 Canonicalization and determinism requirements

Scope canonicalization must be applied before comparison and planning:

* Normalize paths relative to `root_dir` (SSOT).
* Remove redundant segments (e.g., `./`), normalize separators as per project conventions.
* Deduplicate.
* Sort deterministically (stable lexicographic order).

Equivalence must not be vulnerable to ordering differences.

**Rationale:** Without canonicalization, equivalence comparisons can fail due to inconsequential ordering changes, leading to redundant runs and unstable behavior.

---

### 3.3 Per-engine planning model (`EnginePlan`)

Ratchetr constructs an `EnginePlan` per engine per mode. `EnginePlan` captures the complete set of inputs ratchetr will provide to that engine, and serves as the equality basis for deduplication.

#### 3.3.1 Required equality dimensions (per engine)

`EnginePlan` equality must include, for that engine:

* canonicalized resolved target scope
* selected config path (or “none”)
* per-engine extra args / plugin args (as passed to that engine)
* per-engine enablement outcome (enabled vs deselected)
* per-engine profile token (if it affects config/args/scope)
* engine-visible environment values that ratchetr sets/overrides for that engine
* `cwd` / root anchoring where it affects engine execution inputs

#### 3.3.2 Explicit exclusions from equality

`EnginePlan` equality must not include:

* other engines’ configurations, args, or failures
* global run metadata not used by that engine
* execution order

**Rationale:** Deduplication is performed per engine and should not be influenced by unrelated engines or by metadata that cannot affect execution.

---

### 3.4 Mode scheduling and per-engine deduplication

For each engine:

* If requested mode is CURRENT: execute CURRENT plan (no deduplication).
* If requested mode is TARGET: execute TARGET plan (no deduplication).
* If requested mode is BOTH (or default that implies both):

  * Build both plans.
  * If plans are equal after canonicalization: execute **TARGET only** (TARGET is canonical).
  * Otherwise: execute CURRENT then TARGET.

**Rationale:** This avoids running equivalent work twice, while preserving the ability to request a specific mode explicitly. TARGET is canonical for ratcheting eligibility and for consistent “final” reporting.

---

### 3.5 Built-in vs plugin engine responsibilities

#### 3.5.1 Plugin engines are opaque

Ratchetr treats plugin execution mechanics as plugin-owned:

* No assertions are made about executable selection, language runtime, module invocation, or tool-specific execution strategy.
* Ratchetr asserts only the correctness of:

  * resolved inputs it provides to the plugin (targets/config/args/cwd/env inputs under ratchetr control)
  * deterministic planning and equivalence logic based on those inputs
  * classification of results into diagnostics vs engine failures

**Rationale:** Ratchetr must support engines beyond Python (e.g., Rust-native tools) and must not impose a Python-centric execution model on plugins.

#### 3.5.2 Built-in Python engines use module invocation

Where ratchetr owns execution for a built-in Python engine:

* invoke using `sys.executable -m <module>` rather than shelling out to `pyright`/`mypy` executables directly.

**Rationale:** Module invocation reduces ambiguity across uv/venv/CI and avoids reliance on PATH script wrappers.

---

### 3.6 Config selection: deterministic and recorded, not interpreted

Config selection follows a deterministic selection order:

```text
CLI override > env override > ratchetr config > tool-native discovery
```

Ratchetr:

* selects and records the config path used (or “none”)
* does not interpret tool-native config semantics
* applies identical selection rules to CURRENT and TARGET (mode does not affect selection)

**Rationale:** Users need transparency (what config was used) without ratchetr becoming a semantic interpreter of each tool’s configuration language.

---

### 3.7 Explicit empty scope is a configuration error (engine deselection)

If an engine’s configured scope resolves to an explicitly empty set (e.g., an explicit empty list provided by configuration sources), ratchetr:

* deselects the engine
* records a structured configuration error for that engine
* does not execute the engine (no empty-target run)
* allows other engines to proceed normally

**Rationale:** An explicit empty scope is a misconfiguration (or deliberate disabling) and should not be represented as a tool invocation with empty targets (which can trigger tool-specific implicit behaviors).

---

### 3.8 Engine failure semantics (separate from diagnostics)

Ratchetr classifies engine results as follows:

| Scenario                               | Outcome              |
| -------------------------------------- | -------------------- |
| Valid JSON output (any exit code)      | Diagnostics accepted |
| Invalid/missing/unparseable JSON       | `engine_error`       |
| Empty output / no parseable payload    | `engine_error`       |
| Tool missing / OS-level launch failure | `engine_error`       |
| stderr-only output                     | `engine_error`       |

Rules:

* stderr never becomes diagnostics (no pseudo-files such as `<stderr>`)
* engine failures never count as code diagnostics
* engine failures are presented in dashboards in a dedicated section and excluded from diagnostic totals

#### 3.8.1 Required `engine_error` fields

At minimum:

* engine name
* mode
* tool exit code (as returned by the tool, if available)
* argv (opaque, as executed; if plugin-owned, record what plugin reports)
* cwd
* bounded stderr excerpt
* symbolic reason kind (e.g., `TOOL_NOT_FOUND`, `JSON_PARSE_FAILED`, `NO_OUTPUT`, `CRASHED`; `TIMEOUT` reserved without requiring timeouts yet)

**Rationale:** This preserves actionable details while avoiding log explosion, and it supports consistent reporting across engines.

---

## 4. Alternatives Considered

### 4.1 Global deduplication of CURRENT vs TARGET (whole-run equality)

Rejected. Whole-run equality is susceptible to unrelated engine differences and couples deduplication to global state, increasing the chance of missed or redundant work. Per-engine equality is the correct granularity.

### 4.2 Scope-only deduplication (compare just paths)

Rejected. Plans can differ for reasons beyond targets (config, args, enablement). Scope-only comparisons create false equivalence and skip meaningful runs.

### 4.3 Allowing “empty targets” to mean “tool decides scope”

Rejected. This is non-deterministic and tool-dependent, and undermines ratchetr’s role as semantic authority for scoping.

### 4.4 Forcing plugin invocation conventions (e.g., `sys.executable -m`)

Rejected. Plugins may wrap non-Python tools and must remain free to choose execution mechanics. Ratchetr enforces interface-level correctness only.

### 4.5 Treating non-zero exit codes as engine failures even with parseable JSON

Rejected. Many tools emit valid machine-readable diagnostics while returning non-zero codes. Ratchetr accepts parseable JSON as diagnostics and records exit codes separately.

---

## 5. Consequences

### Positive outcomes

* Deterministic and uniform scope resolution across modes with a single caveat.
* Reduced redundant work via per-engine plan-based deduplication.
* Robust equivalence that is not vulnerable to ordering differences.
* Clear separation of engine failures from diagnostics, improving dashboard accuracy and automation reliability.
* Plugin ecosystem remains flexible and language-agnostic.
* Built-in engines gain more reliable invocation under uv/venv/CI.

### Tradeoffs

* Requires careful definition of `EnginePlan` equality fields and canonicalization rules.
* Some tests must be more structured (plan-level) rather than simple “did we call X twice.”
* Tool behaviors remain tool-owned; ratchetr focuses on inputs and classification rather than interpreting config semantics.

---

## 6. Follow-ups and Deferred Items

* Extend symbolic error reason taxonomy and map into the project’s unified exit code system (without hardcoding numeric values here).
* Add timeouts only after explicit override mechanisms exist.
* Expand structured recording of configuration errors (including explicit empty scope) into manifest metadata consistently across commands.
* Harden documentation and help examples to reflect plan-based per-engine deduplication and the single mode caveat.
