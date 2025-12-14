# Engine Execution: Deterministic Scope, Parity, and Error Semantics

## Objective

Make engine execution **correct, deterministic, and mode-consistent**, with:

* one **scope-resolution algorithm**
* one **engine-plan construction pathway**
* no runner-side heuristics
* no implicit scope guessing
* clear separation of **engine failures** vs **code diagnostics**
* deterministic, per-engine deduplication between CURRENT and FULL

PR F **changes runtime behavior** and fixes known correctness bugs.

---

## Final Behavioral Contract

### Scope resolution

There is **exactly one scope-resolution algorithm**, reused verbatim. This is the same resolution pattern used throughout ratchetr.

Precedence:

```text
CLI positional args
> environment variables
> config file
> default ["."]
```

**The only mode difference:**

* **CURRENT** participates in **CLI positional args**
* **FULL** runs without any CLI positional scope input (no CLI positional override can affect FULL)

Nothing else differs (no alternate heuristics, no magic).

> Note: “environment variables” / “config file” refer to the project’s existing scope-path configuration (legacy naming is fine for now). Do not introduce includes/excludes work in this PR.

---

### Engine plan + scheduling rules

Engine execution is planned **per engine**, and deduplication happens **per engine**.

| Mode    | Execution (per engine)                                                               |
| ------- | ------------------------------------------------------------------------------------ |
| CURRENT | Run the engine using scope resolved **with CLI positional args**                     |
| FULL    | Run the engine using scope resolved **without CLI positional args**                  |
| BOTH    | Plan CURRENT and FULL; run CURRENT then FULL **only if the per-engine plans differ** |

**Deduplication rule (deterministic, non-interpretive):**

* If `engine_plan_current == engine_plan_full` (after canonicalization), **skip CURRENT for that engine** and run **FULL only**.

**Canonical run identity:**

* FULL is the canonical run when deduplication occurs (required for ratcheting eligibility).

---

## Required Code Changes

### 1) Delete mode-based scope heuristics and make scope + plan explicit

**Delete or bypass (if properly used for another purpose)** any logic that:

* infers scope from mode
* injects `["."]` as a special FULL behavior (beyond being the default fallback)
* passes empty target lists to runners to “let the tool decide”
* allows engines to decide scope implicitly

#### Primary files to inspect/modify

* `src/ratchetr/audit/execution.py`
* `src/ratchetr/audit/api.py`

#### Concrete change

Remove `_paths_for_mode` (or equivalent) entirely.

Replace with explicit per-mode scope resolution:

```python
current_scope = resolve_scope(
    cli_paths=cli_paths,
    env=env,
    config=config,
    default=["."]
)

full_scope = resolve_scope(
    cli_paths=None,  # <-- the only caveat: FULL has no CLI positional scope input
    env=env,
    config=config,
    default=["."]
)
```

Then construct per-engine plans:

```python
plan_current = build_engine_plan(mode=Mode.CURRENT, scope=current_scope, ...)
plan_full    = build_engine_plan(mode=Mode.FULL,    scope=full_scope,    ...)
```

Scheduling (per engine):

```python
if requested_mode == Mode.CURRENT:
    run(plan_current)

elif requested_mode == Mode.FULL:
    run(plan_full)

else:  # BOTH
    if plan_current == plan_full:
        run(plan_full)  # FULL is canonical
    else:
        run(plan_current)
        run(plan_full)
```

#### Normalization requirements (industry-standard determinism)

The resolver must produce a stable scope representation suitable for equality:

* normalize relative paths against `root_dir` consistently (SSOT)
* preserve file vs dir semantics as provided; do not “guess”
* deduplicate
* sort for stable ordering
* define equality on the canonicalized list/tuple

> Ordering must not create false non-equivalence. Canonicalization is required.

---

### 2) Define per-engine plan equivalence (required to prevent false equivalence)

Deduplication is **not path-only**. Equality is evaluated on the **per-engine execution plan**.

#### `EnginePlan` must include (per engine)

Only the dimensions that can affect how **that engine** runs and can differ between CURRENT and FULL inputs:

* resolved target scope (canonicalized)
* per-engine config selection (path or “none”)
* per-engine extra args / plugin args (as passed to that engine)
* per-engine enablement outcome (enabled vs deselected)
* per-engine profile token (if it affects config/args/scope for that engine)
* engine-visible environment values that ratchetr sets/overrides for that engine
* `cwd` / root anchoring if it is part of the per-engine execution input

#### `EnginePlan` must not include

* other engines’ configuration/args/failures
* global run metadata not used by that engine
* execution order

> This ensures we compare only what could differ for that engine, and avoids coupling equivalence to unrelated engines.

---

### 3) Runner invocation parity (non-negotiable)

CURRENT and FULL invocations for a given engine must be identical except for:

* execution order
* target list (and if identical, CURRENT is skipped for that engine)

This applies to:

* flags
* config selection rules
* plugin args / extra args
* profiles (if relevant)
* working directory (`cwd`)
* environment

#### Enforcement (required design)

* Runners must be **mode-agnostic**
* Runners accept resolved `targets` (and other resolved inputs) and never branch on `Mode`

---

### 4) Invocation method policy (built-ins only; plugins opaque)

#### Built-in engines (implementation standard)

For built-in Python engines where ratchetr controls invocation, standardize to module invocation:

```bash
sys.executable -m pyright ...
sys.executable -m mypy ...
```

Rationale:

* stable across uv/venv/CI
* avoids PATH/script ambiguity
* common in orchestrators

#### Plugin engines (explicitly opaque)

Plugin engines are tool-owned and language-agnostic. Ratchetr must not impose invocation strategy.

* do not assert how the plugin runs its tool
* do not require `-m`, `python`, or any executable naming convention
* parity requirements apply only to the **inputs ratchetr provides**, not the plugin’s internal execution mechanics

#### Files to inspect/modify (built-ins)

* `src/ratchetr/engines/builtin/pyright.py`
* `src/ratchetr/engines/builtin/mypy.py`
* shared execution helpers (e.g., `src/ratchetr/engines/execution.py`)

---

### 5) Config selection rules (consistent across modes; ergonomic; non-interpretive)

Config selection must be deterministic and identical for CURRENT and FULL.

Recommended resolution order:

```text
CLI config override > env override > ratchetr config > tool-native default discovery
```

Rules:

* ratchetr does **not** interpret tool configs; it selects/records what was used.
* record chosen config path (or “none”) in manifest/engine metadata.
* policy is the same for both modes; only scope input differs.

---

### 6) Configuration error: explicit empty scope deselects engine (required)

An explicitly empty include set for an engine is a **configuration error**.

Rules:

* the engine is **deselected**
* the engine is **not executed**
* this is **not** represented as “run with empty targets”
* other engines continue normally
* the configuration error is recorded deterministically (selection-time error, not an execution-time `engine_error`)

---

### 7) Engine error semantics (tighten and enforce)

#### Classification rules

| Scenario                          | Outcome              |
| --------------------------------- | -------------------- |
| Valid JSON output (any exit code) | Diagnostics accepted |
| Invalid/missing JSON              | `engine_error`       |
| Tool crash / not found            | `engine_error`       |
| stderr-only output                | `engine_error`       |

Rules:

* No pseudo-files (e.g., `<stderr>`) ever become diagnostics
* Engine failures never count as diagnostics
* Engine errors are first-class structured data
* Exit codes are recorded and propagated in metadata; numeric mapping is owned by the existing exit code system

#### Required `engine_error` fields (minimum ergonomic set)

* engine name
* mode
* tool exit code (as returned by the tool)
* argv (as executed; opaque)
* cwd
* bounded stderr excerpt
* symbolic reason kind (e.g., `TOOL_NOT_FOUND`, `JSON_PARSE_FAILED`, `NO_OUTPUT`, `CRASHED`; `TIMEOUT` may exist as a placeholder without implementing timeouts yet)

#### Files to inspect/modify

* `src/ratchetr/engines/execution.py` (command runner + JSON parse boundary)
* `src/ratchetr/core/types.py` (or wherever `RunResult.engine_error` is declared)
* dashboard rendering modules (engine failures in dedicated section; excluded from totals)

---

### 8) Update `Mode` documentation (required)

`Mode` must reflect the single caveat clearly:

```python
class Mode(StrEnum):
    """Execution scheduling modes.

    CURRENT:
        Resolve scope using CLI > env > config > default.

    FULL:
        Resolve scope using env > config > default
        (no CLI positional scope input participates).

    BOTH:
        Plan CURRENT and FULL per engine and run CURRENT only
        when the per-engine plans differ.
    """
```

No other semantics should be embedded in mode docs.

---

## PR F Acceptance Criteria

* One scope resolver is used for both modes; only CLI positional scope input differs
* Per-engine plan construction is deterministic and canonicalized (order-invariant scope)
* Deduplication is per-engine and compares per-engine plan dimensions (not path-only)
* FULL is the canonical run when deduplication occurs
* No engine infers scope implicitly; targets are always explicit
* No engine receives an empty target list unless the resolved scope is truly empty (default `["."]` prevents this in normal operation)
* Explicit empty include configuration deselects the engine and records a configuration error (no execution)
* Engine failures are structured `engine_error` and never appear as diagnostics
* Built-in engines use `sys.executable -m …` where ratchetr owns invocation; plugin engines remain opaque
* Per-engine config selection is deterministic and recorded (not interpreted)
