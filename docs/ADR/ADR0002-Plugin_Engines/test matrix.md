# PR-F Testing Matrix v2 — Engine Execution Determinism, Per-Engine Equivalence, and Engine-Error Semantics

## 0) Test harness and invariants

### 0.1 Canonical objects (test doubles)

* **ResolvedScope**: canonicalized scope list of root-relative paths.
* **EnginePlan** (per engine): the complete, engine-specific input bundle ratchetr will use for execution *or* determine deselection.
* **RunPlan**: ordered list of `EngineRun` items: `{engine_id, mode, engine_plan}`.

### 0.2 Required normalization rules (must be implemented and tested)

These are required to prevent equivalence traps.

#### Scope normalization (required; order-invariant)

* Normalize path strings to canonical root-relative form.
* Deduplicate.
* Sort (stable lexicographic) to make equality reliable.
* Equality is defined on the canonicalized sequence.

> This is non-negotiable: equivalence decisions must not be susceptible to path ordering differences.

#### Args normalization (engine-provided extra args / plugin args)

Ratchetr must be deterministic about *how it compares and passes args*, but it must not invent semantics.

* Treat the per-engine args value as an **ordered list** by default.
* Canonicalize only *representation* (e.g., trimming, stable splitting rules if any exist in your interface).
* Do **not** reorder args unless the interface explicitly defines them as order-insensitive.

**Test requirement:**

* If args are order-sensitive in your interface, then reordered args must be treated as **not equivalent**.
* If you have any interface surface that is defined as order-insensitive, then it must be canonicalized and tested as order-insensitive.

> Paths are always canonicalized order-insensitive. Args are only order-insensitive if your interface explicitly defines them that way.

### 0.3 Per-engine equivalence definition (authoritative for PR-F)

Deduplication is **per engine** using a per-engine equivalence function:

`EnginePlan(CURRENT) == EnginePlan(FULL)` iff all **engine-relevant plan dimensions that could differ between CURRENT and FULL** match after canonicalization.

#### Must include (for that engine)

Only the parts that can affect *that engine’s run* and can differ between CURRENT vs FULL configuration inputs:

* **Effective target scope** (ResolvedScope)
* **Per-engine config selection** (path or “none”)
* **Per-engine extra args / plugin args** (as passed to that engine)
* **Per-engine enablement / deselection outcome** (including configuration error deselection)
* Any **per-engine profile token** (if it affects config/args/scope for that engine)
* Any **engine-visible env** that ratchetr intentionally sets/overrides for that engine
* **cwd/root anchoring** if it affects how that engine is invoked (typically shared, but if it is part of the per-engine execution input, it must be compared)

#### Must NOT include (explicitly excluded)

* Other engines’ configuration, args, enablement state, or failures
* Any global run metadata not used by the engine
* Execution order

> Key correction: equivalence is not “whole run.” It is strictly the dimensions that matter for **that engine**.

### 0.4 Mode scheduling rule (per engine)

For requested mode `BOTH` (or default BOTH):

* Compute per-engine `plan_current` and `plan_full`
* If plans are equal for that engine: run **FULL only** for that engine (canonical for ratcheting)
* Else: run CURRENT then FULL for that engine

For requested mode `CURRENT` or `FULL`, do not deduplicate; honor request.

---

## 1) Scope Resolution Suite (pure)

Validate: `resolve_scope(mode, cli_paths, env_paths, config_paths, default=["."]) -> ResolvedScope`

### 1.1 Precedence correctness

**SR-PREC-001 (CURRENT uses CLI):**

* mode: CURRENT
* cli: [`src`, `tests`]
* env: [`lib`]
* config: [`pkg`]
* default: [`.`]
* expected: [`src`, `tests`]

**SR-PREC-002 (FULL has no CLI scope input):**

* mode: FULL
* cli: [`src`, `tests`] (supplied but must not participate)
* env: [`lib`]
* config: [`pkg`]
* default: [`.`]
* expected: [`lib`]

**SR-PREC-003 (CURRENT falls back to ENV when CLI omitted):**

* mode: CURRENT
* cli: []
* env: [`lib`]
* config: [`pkg`]
* default: [`.`]
* expected: [`lib`]

**SR-PREC-004 (FULL falls back to CONFIG when ENV omitted):**

* mode: FULL
* cli: [`src`]
* env: []
* config: [`pkg`]
* default: [`.`]
* expected: [`pkg`]

**SR-PREC-005 (DEFAULT applies when nothing provided):**

* mode: CURRENT
* cli/env/config: []
* default: [`.`]
* expected: [`.`]

**SR-PREC-006 (DEFAULT applies for FULL as well):**

* mode: FULL
* cli/env/config: []
* default: [`.`]
* expected: [`.`]

### 1.2 Ordering and dedup (equivalence trap prevention)

**SR-ORD-001 (scope ordering canonicalization):**

* mode: CURRENT
* cli: [`b/b.py`, `a/a.py`, `a/z.py`]
* expected: [`a/a.py`, `a/z.py`, `b/b.py`]

**SR-DEDUP-001 (scope dedup canonicalization):**

* mode: CURRENT
* cli: [`src`, `src`, `./src`]
* expected: [`src`]

**SR-NORM-001 (dot segments normalized):**

* mode: CURRENT
* cli: [`./src/./pkg//a.py`]
* expected: [`src/pkg/a.py`]

**SR-EQUIV-TRAP-001 (ordering does not change equality):**

* mode: CURRENT
* cli: [`tests`, `src`]
* expected: [`src`, `tests`]
* and `ResolvedScope(["src", "tests"]) == ResolvedScope(["tests", "src"])`

---

## 2) Per-Engine Plan Construction Suite (pure)

Validate: `build_engine_plan(engine_id, mode, resolved_scope, config_selection, engine_args, root_dir, engine_env, profile_token, …) -> EnginePlan`

### 2.1 EnginePlan excludes unrelated engines (corrected emphasis)

**EP-DIM-001 (other engines do not affect EnginePlan equivalence):**

* engine A plan built with:

  * engineA_args: [`--x`]
  * engineB_args: [`--y`] (present in environment/config)
* expected:

  * EnginePlan(A) does not vary if only engineB_* inputs change
  * Equivalence for A is based only on A-relevant dimensions

### 2.2 Config selection parity per engine

**EP-CFG-001 (config selection identical across modes when sources identical):**

* engine: A
* current config selection input yields `cfgA.toml`
* full config selection input yields `cfgA.toml`
* expected:

  * plan_current.config == plan_full.config == `cfgA.toml`

### 2.3 Args handling (explicitly avoids semantic invention)

**EP-ARGS-ORDER-001 (args are order-sensitive by default):**

* engine: A
* current args: [`--foo`, `--bar`]
* full args: [`--bar`, `--foo`]
* expected: plans not equal (unless your interface explicitly defines these args as order-insensitive)

**EP-ARGS-ORDER-002 (args determinism when collected from multiple sources):**

* engine: A
* inputs collected from env/config/cli (as applicable)
* expected:

  * the resulting args list is deterministic
  * repeated runs produce identical `engine_args` ordering

> This prevents accidental nondeterminism introduced by merges or dict iteration, without inventing “args are a set.”

---

## 3) Per-Engine Equivalence + Scheduling Suite (pure)

Validate: `plan_engine_runs(requested_mode, plan_current, plan_full) -> [EngineRun]`

### 3.1 Dedup only when BOTH/default requested

**MS-ENG-001 (BOTH + plans differ → run CURRENT then FULL):**

* requested_mode: BOTH
* plan_current.targets: [`src`]
* plan_full.targets: [`.`]
* other A-relevant plan dimensions equal
* expected runs: [`CURRENT`, `FULL`]

**MS-ENG-002 (BOTH + plans equal → run FULL only):**

* requested_mode: BOTH
* plan_current == plan_full
* expected runs: [`FULL`] (canonical)

**MS-ENG-003 (CURRENT-only never deduped):**

* requested_mode: CURRENT
* plan_current == plan_full
* expected runs: [`CURRENT`]

**MS-ENG-004 (FULL-only never deduped):**

* requested_mode: FULL
* plan_current == plan_full
* expected runs: [`FULL`]

### 3.2 False equivalence guards (engine-relevant non-path parameters)

**MS-ENG-NEQ-001 (targets equal but config differs → no dedup):**

* requested_mode: BOTH
* targets equal
* plan_current.config != plan_full.config
* expected: [`CURRENT`, `FULL`]

**MS-ENG-NEQ-002 (targets equal but args differ → no dedup):**

* requested_mode: BOTH
* targets equal
* args differ
* expected: [`CURRENT`, `FULL`]

**MS-ENG-NEQ-003 (targets equal but enablement differs → no dedup):**

* requested_mode: BOTH
* one plan enabled, the other deselected (e.g., config error)
* expected: do not treat as equal; scheduler behavior reflects deselection rules (see §4)

### 3.3 Ordering trap guards (required)

**MS-ENG-ORDTRAP-001 (targets differ only by ordering → dedup):**

* requested_mode: BOTH
* plan_current.targets: [`src`, `tests`]
* plan_full.targets: [`tests`, `src`]
* expected: plans equal → [`FULL`]

---

## 4) Configuration Error Handling Suite (selection-time; no execution)

### 4.1 Explicit empty scope is a configuration error → engine deselected

**CFG-ERR-EMPTY-001 (explicit empty includes deselect engine):**

* engine: A
* resolved includes from env/config is explicitly `[]`
* expected:

  * engine marked **DESELECTED**
  * error recorded as **CONFIGURATION_ERROR** (selection-time)
  * engine not executed in either mode where empty applies
  * no empty targets passed to runner

**CFG-ERR-EMPTY-002 (deselection is per engine; others proceed):**

* engine A: explicit empty includes
* engine B: valid includes
* expected:

  * A not executed, config error recorded
  * B executed normally

**CFG-ERR-EMPTY-003 (deselection does not masquerade as scope override):**

* expected:

  * deselected engine has a configuration error record
  * it is not represented as “ran with empty scope”
  * it does not produce `engine_error` (no execution occurred)

---

## 5) Execution Boundary Suite (stubbed; no real tools)

Validate classification into diagnostics vs engine_error, with symbolic kinds + descriptions.

### 5.1 Engine failure kinds (symbolic; no numeric codes here)

* `ENGINE_OUTPUT_PARSE_FAILED`: stdout expected parseable, but wasn’t
* `ENGINE_NO_PARSEABLE_OUTPUT`: no usable payload
* `ENGINE_TOOL_NOT_FOUND`: OS-level invocation failure
* `ENGINE_CRASHED`: unexpected exception at execution boundary

**EE-CLASS-001 (valid JSON output → diagnostics accepted):**

* tool_exit: any (including non-zero)
* stdout: valid JSON payload
* expected:

  * diagnostics present
  * engine_error absent
  * record tool_exit in engine metadata

**EE-CLASS-002 (invalid JSON → ENGINE_OUTPUT_PARSE_FAILED):**

* tool_exit: any
* stdout: invalid JSON
* expected:

  * diagnostics empty
  * engine_error present with kind `ENGINE_OUTPUT_PARSE_FAILED`
  * engine_error contains: engine_id, mode, argv (opaque), cwd, tool_exit, stderr excerpt

**EE-CLASS-003 (empty stdout → ENGINE_NO_PARSEABLE_OUTPUT):**

* stdout: ""
* stderr: any
* expected:

  * engine_error kind `ENGINE_NO_PARSEABLE_OUTPUT`

**EE-CLASS-004 (tool not found → ENGINE_TOOL_NOT_FOUND):**

* simulate OS-level not found
* expected:

  * engine_error kind `ENGINE_TOOL_NOT_FOUND`

**EE-NOSTDERR-001 (stderr never becomes diagnostics):**

* stderr contains diagnostic-looking text
* stdout empty/unparseable
* expected:

  * diagnostics empty
  * engine_error present
  * no pseudo diagnostic entries derived from stderr

---

## 6) Plugin Interface Robustness Suite (no invocation assertions)

### 6.1 No assumptions about plugin execution mechanics

**PLG-OPAQUE-001 (no assertions about how plugin runs):**

* plugin engine returns:

  * argv: any list (opaque) OR no argv at all (plugin-owned)
  * tool_exit: any
* expected:

  * tests assert only:

    * ratchetr passes EnginePlan inputs consistently
    * per-engine equivalence uses EnginePlan dimensions (not invocation mechanics)
    * engine_error classification rules apply to results

### 6.2 Parity invariants for plugins are interface-level only

**PLG-PAR-001 (mode does not change per-engine parameterization besides CLI scope participation):**

* requested_mode: BOTH
* plugin engine configured identically via env/config
* expected:

  * plan_current differs from plan_full only when CLI scope influences CURRENT targets
  * otherwise dedup to FULL

---

## 7) Determinism Suite (mixed)

### 7.1 Deterministic ordering

**DT-ORDER-001 (CURRENT then FULL when both run):**

* expected: per-engine run ordering stable: CURRENT then FULL (when both planned)

### 7.2 Deterministic output ordering within records

**DT-ORDER-002 (recorded run list stable):**

* expected: recorded runs stable under repeated executions with same inputs

### 7.3 Equivalence trap prevention: reordering inputs does not change plan

**DT-EQUIV-001 (reordered scope inputs → identical plan):**

* Same scope paths but reordered CLI/env/config sources
* expected:

  * identical ResolvedScope after canonicalization
  * identical EnginePlan
  * identical RunPlan and dedup/skip outcomes

---

## PR-F Acceptance Coverage Checklist

This matrix verifies PR-F guarantees:

* One precedence chain, reused verbatim
* FULL has no CLI positional scope input; CURRENT does
* Dedup/skip is **per engine**, not global
* Dedup occurs only when BOTH/default requested
* Dedup compares **per-engine plan dimensions that could differ for that engine**, not other engines
* Scope ordering differences do not cause false non-equivalence
* Args ordering is treated deterministically without inventing semantics (order-sensitive by default unless explicitly defined otherwise)
* Explicit empty scope is a configuration error → engine deselected (selection-time)
* engine_error vs diagnostics classification is deterministic using symbolic kinds + descriptions (no numeric code invention here)
* Plugins remain opaque: no assertions about how they execute tools, only robust interface behavior
