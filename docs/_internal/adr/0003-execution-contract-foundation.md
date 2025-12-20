# ADR-0003 Execution Contract Foundation: Mode model; source/precedence boundaries; Resolution Domains; Runner vs Executor

**Purpose:** Establish the execution contract boundaries across Resolution, Planning, and Execution, including mode model and source precedence responsibilities.
**Status:** Normative (Draft)
**Owned concepts:**

- Mode model and source/precedence boundaries
- Resolution Domains partitioning and immutability guarantees
- Runner vs Executor responsibility boundary

**Primary links:** `docs/reference/run_summary.md`, `docs/reference/findings.md`, `docs/reference/run_artifacts.md`, `docs/reference/error_codes.md`

## Must not contain

- Exhaustive schemas or field catalogs (owned by reference specs)
- Selector/path/link algorithms
- CLI inventories or parity tables

## Context and Problem Statement

Ratchetr commands must behave deterministically and make all policy decisions in a
single place. Today, resolution decisions can leak into planning or execution
layers, making runs harder to reason about and harder to test. This ADR defines
where decisions are made, what becomes immutable, and how decisions are surfaced
to users and artifacts.

## Decision Drivers

- Determinism: the same inputs produce the same resolved policy.
- Decision visibility: users can see what was decided and why.
- Immutability: resolved values are not recomputed later.
- Separation of concerns: planning and execution do not reinterpret inputs.
- Extensibility: future features (overlays, new commands) fit without redesign.

## Considered Options

### Option A — Status quo (decisions spread across layers)

Rejected. Hidden precedence and duplicated resolution logic create drift between
planning and execution.

### Option B — Single monolithic plan object

Rejected. Blurs policy decisions with runtime observations; weakens auditability.

### Option C — Explicit boundary: Resolution → Plan → Run

Accepted. Decisions happen once during Resolution; Planning is a pure derivation;
Execution only consumes the plan.

## Decision Outcome

### Pipeline and immutability

Adopt a strict pipeline:

```text
CommandSpec (normalized argv)
  -> Resolution (only decision point)
  -> CommandPolicy (immutable)
  -> Planning (pure derivation)
  -> CommandPlan (immutable)
  -> Execution (Runner/Executor) -> CommandRun
```

Rules:

- Resolution happens exactly once. Planning and Execution must not rediscover
  config, reapply precedence, or re-interpret selectors.
- Policy and Plan objects are immutable. Runtime observations belong in Run
  records, not policy or plan.

### Resolution Domains (policy partitioning)

Resolution produces a `CommandPolicy` composed of domains. Each domain captures
resolved values and provenance. The exact schema is owned by reference specs,
but the domains are mandatory and stable:

- Workspace/Mode domain: project vs ad-hoc mode and boundaries.
- Sources domain: CLI/ENV/config/default provenance and disabled sources.
- Paths domain: base/project-root normalization and absolute gating.
- Scope domain: resolved selection tokens and target boundaries.
- Engine domain: resolved engine inputs used by planning.
- Artifacts domain: required run artifacts and persistence gating.
- Output/Streams domain: stdout/stderr/reporting policy.
- Exit domain: exit status mapping rules.

### Decision visibility

Decision visibility is mandatory and split across artifacts:

- `run_summary` (see `docs/reference/run_summary.md`) discloses mode, inputs,
  disabled sources, resolved boundaries, and high-level outcomes.
- `findings` (see `docs/reference/findings.md`) records structured diagnostics
  including resolution-time errors (e.g., disallowed absolute paths).
- `run_artifacts` (see `docs/reference/run_artifacts.md`) defines the minimal
  artifact set and the Resolution Log for deep inspection.

### CLI boundary normalization

Macro flags and argv normalization happen before `CommandSpec` is constructed.
Macro tokens are expanded and removed at the argv boundary; only normalized
argv is parsed into `CommandSpec`.

### Runner vs Executor boundary

- Runners orchestrate a full command run and emit `CommandRun` artifacts.
- Executors perform a single unit of work (engine invocation, renderer, or
  persistence action). Executors never make policy decisions.

### Failure on silent degradation

If any runtime-affecting input cannot be applied as specified and ignoring it
would change effective scope or configuration, Resolution must fail before
Planning. The failure is emitted as an Error Finding and surfaced in the run
summary.

## Consequences

- Planning and execution are simpler and testable (no hidden policy logic).
- New features (overlays, new commands) can be added by extending Resolution
  Domains without changing the pipeline.
- Requires strict layering enforcement in code review and tests.

## Links

- `docs/reference/run_summary.md`
- `docs/reference/findings.md`
- `docs/reference/run_artifacts.md`
- `docs/reference/error_codes.md`
- `docs/_internal/adr/0006-paths-foundation.md`

## Draft log

### 2025-12-20 — Phase 2 rewrite

- **Change:** Rewrote ADR-0003 with Resolution→Plan→Run pipeline, Resolution Domains, and decision visibility.
- **Preservation:** P-0001, P-0002, P-0003, P-0004, P-0005, P-0006 (see CF-0001..CF-0006).
- **Overlay:** OVL-0002, OVL-0004.
- **Mapping:** MAP-0001..MAP-0007.
- **Supersedence:** N/A.
- **Notes / risks:** Requires follow-through in reference specs and run artifacts.
