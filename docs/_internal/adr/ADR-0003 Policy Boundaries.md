# ADR-0003: Policy Boundaries, Decision Visibility, and Immutability

* **Status:** Proposed
* **Date:** 2025-12-15
* **Deciders:** Ratchetr maintainers
* **Tags:** architecture, policy, determinism, boundaries, execution, planning

---

## Context and problem statement

Ratchetr is a multi-command CLI that must behave deterministically across commands and across time. It resolves and applies *policy* decisions such as:

* which workspace/project is being operated on (root/config selection)
* what scope is targeted (`TARGET`/`include`/`exclude`, base semantics)
* which engines run and with what effective options
* where outputs go (manifest, dashboards, logs, cache)
* what is emitted to stdout/stderr
* what is written under dry-run / no-cache policies
* how exit codes are computed

Today, these decisions can leak into helpers, planners, or executors, creating black-box behavior and diverging behavior between “planning” and “execution.” It also makes it difficult to add features like directory-level engine configuration (e.g., `ratchetr.dir.toml`) without double-scanning, inconsistent deduping, or hidden precedence.

**Problem statement:**
We need a single, enforceable boundary that defines where decisions are allowed to be made, ensures those decisions are immutable once resolved, and makes decisions inspectable/testable—without coupling the design to any one command (audit today, scan later).

---

## Decision drivers

1. **Determinism:** the same inputs must produce the same outcomes.
2. **Decision visibility:** “what happened and why” must be discoverable without reading deep call stacks.
3. **Immutability:** once decisions are resolved, execution must not mutate them.
4. **Separation of concerns:** avoid “policy blobs” and avoid policy being re-derived during execution.
5. **Extensibility:** support future features cleanly (scan command, richer stdout output, per-directory engine configs).
6. **Testability:** policy and boundaries must be unit-testable and enforceable via import layering.

---

## Considered options

### Option A — Status quo (decisions spread across layers)

**Description:** Helpers/planners/executors may infer defaults, re-resolve paths, or interpret scope.
**Result:** Rejected.

* Pros: minimal refactor in the short term.
* Cons: unstable behavior, duplicated logic, hidden precedence, planning/execution divergence.

### Option B — One flat “Plan” object that holds everything

**Description:** Create a single plan object that includes raw inputs, resolved values, and runtime notes.
**Result:** Rejected.

* Pros: fewer types.
* Cons: ambiguity (spec vs plan vs runtime), “notes” become unstructured, boundaries stay porous.

### Option C — Explicit pipeline: **Spec → Policy → Plan → Run**

**Description:**

* **Spec:** declared user intent (inputs)
* **Policy:** resolved, immutable decisions (with provenance)
* **Plan:** executable blueprint derived from policy (pure derivation)
* **Run:** runtime record/results of executing the plan

**Result:** Accepted.

---

## Decision outcome

Adopt a strict, project-wide pipeline and boundary rules:

### 1) Pipeline

```text
CommandSpec
  |
  v
Resolve Policy (the only place decisions are made)
  |
  v
CommandPolicy (immutable; attributed decisions)
  |
  v
Build Plan (pure derivation; no discovery/defaulting)
  |
  v
CommandPlan (immutable; executable blueprint)
  |
  v
Runner executes plan -> CommandRun (runtime record)
```

### 2) Immutability

* **Policy is immutable** during planning and execution.
* **Plans are immutable** during execution.
* Runtime observations belong in **Run records**, not policy or plan.

### 3) Decision visibility

* Every resolved value must carry **source attribution**: `CLI | ENV | CONFIG | DEFAULT`.
* Policy resolution produces a structured **Decision Log** and structured **Findings** (no unstructured “notes”).

### 4) Executors do not decide

* Executors do not apply precedence.
* Executors do not “fix up” missing scope.
* Executors do not rediscover config/root.
* Executors execute **exactly** what is described in the plan.

---

## Policy domains

Policy is a composition of orthogonal domains. Each domain produces an immutable object.

```text
CommandPolicy
├─ WorkspacePolicy   (where am I? which config applies?)
├─ ScopePolicy       (what am I scanning? how are tokens interpreted?)
├─ EnginePolicy      (which engines? effective per-engine settings inputs)
├─ OutputPolicy      (where do artifacts go?)
├─ StreamPolicy      (stdout/stderr and presentation)
├─ ManifestPolicy    (manifest content rules + schema/version + path representation)
├─ CachePolicy       (cache enablement + persistence rules)
├─ WritePolicy       (dry-run and write gating)
└─ ExitPolicy        (how results map to exit codes)
```

**Important separation:**

* **OutputPolicy** decides *destinations* (paths/targets).
* **ManifestPolicy** decides *content and representation* (what the manifest contains, schema/versioning, how paths are represented inside it).
* **StreamPolicy** decides stdout/stderr routing and formatting policy.
* **WritePolicy** gates all writes (including whether cache persistence counts as a write under dry-run).

---

## Boundary rules

### What Policy may do

Policy resolution is the only layer allowed to:

* read env vars (as inputs)
* locate/load config (as inputs)
* decide precedence
* decide defaulting behavior
* interpret target/base tokens
* generate warnings/findings for resolution outcomes

### What Planning may do

Planning is pure derivation from policy:

* convert policy to executable units (invocations, writes, render operations)
* canonicalize and order for determinism
* compute dedupe decisions using canonical plan identity

Planning must not read env/config or rediscover workspace.

### What Execution may do

Execution consumes the plan:

* run engines/tools
* gather results
* render outputs
* write artifacts **only if allowed** by WritePolicy
* compute exit status **only as directed** by ExitPolicy

Execution must not reinterpret scope/paths or apply precedence.

---

## Runner vs Executor roles

* **Runner:** orchestrates a whole command run; coordinates multiple executors; produces `CommandRun`.
* **Executor:** executes a single work unit (e.g., one engine invocation, one renderer, one persistence action).

Naming rule: if it executes a tool/work item, it is an **executor** (not a runner). Runners are orchestration only.

---

## EnginePlan and directory-level engine configuration

### Requirement: EnginePlan must represent effective execution configuration

If the same engine can be run with different effective settings due to directory-level configuration (e.g., `ratchetr.dir.toml` overlays), then the **unit of dedupe and execution must include those effective settings**.

Therefore:

1. `EnginePlan` (or the per-invocation plan type) must include:

   * effective include/exclude for that invocation
   * effective `config_file`/profile/plugin args for that invocation
   * any other options that change tool behavior
   * the resolved scope segment it will run against

2. Planning must be capable of generating **multiple invocations per engine** when overlays imply different effective configurations.

### Preventing double scanning: partitioned invocations (disjoint scopes)

When overlays exist, the planner must produce disjoint invocations such that parent runs do not rescan child override subtrees.

Example (conceptual):

```text
Workspace root
├─ (base engine settings)
│   ├─ src/                      -> invocation A (scope = src minus overridden subtrees)
│   └─ tests/                    -> invocation A
└─ src/foo/ (dir override exists) -> invocation B (scope = src/foo, config = foo override)
```

This keeps execution deterministic and dedupe correct: invocations differ if effective engine settings differ.

**Note:** Whether directory overrides are currently wired end-to-end is an implementation concern; this ADR requires that the architecture and plan identity support it without redesign later.

---

## Structured findings (replacing unstructured notes)

Policy and scope findings must be structured:

```text
Finding
- code: enum
- severity: info|warn|error
- subject: { token?, path?, engine? }
- message: string
- data: optional structured payload
```

No untyped “notes” lists. This enables stable testing and consistent UX.

---

## Recommended tree structure

The following structure makes the boundary enforceable and reviewable. Exact naming may vary, but the separation must remain.

```text
src/ratchetr/
  policy/
    types.py            # Resolved[T], DecisionLog, Finding, Source
    workspace.py         # WorkspacePolicy resolution
    scope.py             # ScopePolicy resolution
    engines.py           # EnginePolicy resolution (+ overlay semantics inputs)
    outputs.py           # OutputPolicy resolution
    streams.py           # StreamPolicy resolution
    manifest.py          # ManifestPolicy resolution
    cache.py             # CachePolicy resolution
    write.py             # WritePolicy resolution
    exit.py              # ExitPolicy resolution
    resolve.py           # resolve_<command>_policy entrypoints
  planning/
    build_audit_plan.py  # policy -> audit plan (pure derivation)
    build_*_plan.py       # other commands
  runtime/
    runners/
      audit.py           # command-level runner(s)
      dashboard.py
      manifest.py
      query.py
      ratchet.py
    executors/
      engine.py          # EngineExecutor
      render.py          # render executors
      persist.py         # persistence executors
    records/
      run.py             # CommandRun / EngineRunResult / timings
```

---

## Consequences

### Positive

* Deterministic behavior through a single decision point.
* Planning/execution divergence becomes structurally difficult.
* Easy to add commands (scan later) without copying precedence logic.
* Directory-level engine configuration becomes a first-class supported capability via partitioned invocations and plan identity.

### Negative / costs

* Refactor required to relocate implicit decisions into policy.
* More types (intentional), requiring discipline and a consistent naming taxonomy.
* Requires boundary enforcement (tests + review rules) to prevent regressions.

---

## Compliance and enforcement

1. **Import layering rule:** planning/runtime modules must not import env/config discovery utilities.
2. **Policy unit tests:** assert attribution, precedence, and emitted findings.
3. **Boundary tests:** ensure executors do not perform policy resolution (e.g., forbid env/config reads in executor paths).
4. **Immutability checks:** policy and plan objects are frozen/immutable.

---

## Implementation notes (non-binding)

A practical adoption path:

1. Introduce `Resolved[T]`, `DecisionLog`, `Finding` and the `Source` enum.
2. Implement `WorkspacePolicy` first and route all commands through it.
3. Move stdout/stderr behavior into `StreamPolicy` and stop emitting directly from deep helpers.
4. Convert one command end-to-end (audit) to validate the boundary.
5. Add directory-override-aware planning once the policy/plan boundary is solid (generate disjoint engine invocations).

---

## Out of scope

* Exact include/exclude semantics and pattern language definition (separate ADR).
* Exact engine equivalence/dedup rules beyond “plan identity must include effective settings” (separate ADR).
* Implementing the scan command itself (future work).

---

## Related decisions

* ADR-0001: Include/Exclude semantics
* ADR-0002: Plugin engines planning and equivalence

---
