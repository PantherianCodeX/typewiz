# Updated Reference Implementation Outline: ADR-000X (POSIX-only separators, JSON-only env, replacement precedence, overwrite outputs, stable ordering)

**Status:** Implementation blueprint
**Derived from:** ADR-000X (Accepted, 2025-12-13)
**Scope:** Module boundaries, public interfaces, invariants, and the minimal algorithmic commitments required to implement ADR-000X without semantic drift.

---

## 1) Non-negotiable invariants (enforced end-to-end)

### 1.1 Semantic authority

Ratchetr MUST compute and own:

* the canonical candidate file set (discovery)
* the in-scope set (includes/excludes evaluation)
* final correctness by filtering diagnostics to the in-scope set, regardless of engine invocation breadth

### 1.2 Safety

Ratchetr MUST:

* never scan outside `--root`
* never traverse symlinks (including any symlink component)
* emit warnings and persist them into the manifest for:

  * out-of-root skips
  * symlink skips

### 1.3 Portability and normalization

* Canonical paths MUST be root-relative, normalized, POSIX-separated (`/`).
* Pattern strings MUST be interpreted using POSIX separators only; `\` has no separator meaning in v1.

### 1.4 Determinism

Stable ordering MUST be applied to:

* discovered candidates (by canonical `rel_posix`)
* the eligible/in-scope list
* diagnostics ordering in emitted artifacts
* dashboards/manifest sections ordering

Byte-identical output is not required.

### 1.5 Precedence and input encoding

* `includes` and `excludes` are resolved per-source with replacement semantics: CLI > env > config > defaults.
* Env vars are JSON list of strings only.

### 1.6 Output semantics

* Output targets are treated as files by default; trailing `/` indicates directory intent.
* `--save-as` / `--dashboard` overwrite existing output files by default.
* Output destination collisions within a single invocation MUST be detected and treated as fatal errors.

---

## 2) Module layout and responsibilities

The outline assumes your package root is `ratchetr/` (adapt under `src/ratchetr/` if needed).

### 2.1 `ratchetr/core/paths.py`

**Responsibilities:**

* Resolve and normalize filesystem paths to canonical root-relative POSIX paths
* Enforce root boundary checks
* Detect symlink components (fail-closed)

**Public API:**

* `@dataclass(frozen=True) RootedPath`

  * `abs_path: Path`
  * `rel_posix: str`  # canonical
* `def canonicalize(root: Path, candidate: Path) -> RootedPath | None`

  * Returns `None` when candidate resolves outside root.
* `def has_symlink_component(root_abs: Path, candidate_abs: Path) -> bool`

  * Returns True if any component under root is a symlink; **fail-closed** on stat errors.

**Key commitments:**

* `canonicalize()` MUST produce `rel_posix` with `/` only and no `.` segments.
* `canonicalize()` MUST NOT accept absolute pattern matching; it returns root-relative representation only.

---

### 2.2 `ratchetr/core/warnings.py`

**Responsibilities:**

* Define structured warning events
* Provide a sink for collection and manifest serialization

Warnings are persisted to the manifest in **emission order**. Implementations must ensure emission is deterministic by relying on stable traversal order (discovery) and stable evaluation order (scope evaluation and unmatched-pattern checks).

**Public API:**

* `class WarningCode(Enum)`:

  * `PATH_OUTSIDE_ROOT`
  * `SYMLINK_SKIPPED`
  * `PATTERN_UNMATCHED`  # informational warning for patterns matching nothing in the run
* `@dataclass(frozen=True) WarningEvent`

  * Required fields:

    * `code: WarningCode`
    * `severity: Literal["warning"]`
    * `message: str`
    * `action: Literal["skipped","info"]`  # skipped for safety, info for unmatched pattern
    * `root: str`
    * `path_input: str | None`
    * `path_resolved: str | None`
    * `pattern: str | None`
    * `source: Literal["discovery","scope","config","engine","output"]`
* `class WarningSink(Protocol)`

  * `emit(event: WarningEvent) -> None`
  * `events() -> Sequence[WarningEvent]`
* `class CollectingWarningSink(WarningSink)`

**Key commitments:**

* Discovery must emit `PATH_OUTSIDE_ROOT` and `SYMLINK_SKIPPED`.
* Scope evaluation must emit `PATTERN_UNMATCHED` after discovery+filtering, when applicable.

---

### 2.3 `ratchetr/core/patterns.py`

**Responsibilities:**

* Parse patterns into a structured spec
* Validate constraints (negation allowed only where enabled; separators are POSIX-only)
* Match patterns against canonical root-relative POSIX paths

**Public API:**

* `class PatternError(ValueError)`
* `class PatternKind(Enum)`:

  * `SINGLE_LITERAL`
  * `SINGLE_WILDCARD`
  * `MULTI_SEGMENT`
* `@dataclass(frozen=True) PatternSpec`

  * `raw: str`
  * `anchored: bool`
  * `dir_only: bool`
  * `negated: bool`
  * `segments: tuple[str, ...]`
  * `kind: PatternKind`
* `def parse_pattern(raw: str, *, allow_negation: bool) -> PatternSpec`
* `def matches(spec: PatternSpec, rel_posix: str) -> bool`

**Key commitments:**

* Reject patterns containing `\` **only if** you want strictness; ADR states `\` is literal, so parsing MUST allow it.
* Single-segment split:

  * literal token matches any segment (anchored = first segment, floating = any)
  * wildcard token matches basename only (anchored = root-only basename, floating = any basename)
* Directory-only implies subtree semantics (as if appending `/**` for file candidates).
* Multi-segment floating patterns are suffix matches starting at any segment boundary; anchored patterns match from root.
* `**` implemented via DP/memoization (no whole-path regex compilation).

---

### 2.4 `ratchetr/core/scope.py`

**Responsibilities:**

* Compile includes/excludes into `PatternSpec` lists
* Apply include/exclude algorithm and negation semantics
* Apply replacement-precedence resolution at the “effective patterns” boundary (or keep this in config; see 2.6)
* Track which patterns matched at least one candidate for unmatched-pattern warnings

Unmatched-pattern warnings (`PATTERN_UNMATCHED`) MUST be evaluated and emitted only for patterns sourced from **CLI/env/config** (not defaults). Emission order should follow:

1. discovery-time warnings (as encountered), then
2. scope-time unmatched-pattern warnings (in deterministic pattern order).

**Public API:**

* `class ScopeConfigError(ValueError)`
* `@dataclass(frozen=True) EffectiveScope`

  * `includes: tuple[PatternSpec, ...]`
  * `excludes: tuple[PatternSpec, ...]`
* `@dataclass(frozen=True) ScopeMatchStats`

  * `include_hits: dict[str, int]`  # raw pattern -> match count
  * `exclude_hits: dict[str, int]`
* `def compile_scope(includes: Sequence[str], excludes: Sequence[str]) -> EffectiveScope`

  * MUST reject negation in includes.
* `def in_scope(scope: EffectiveScope, rel_posix: str) -> bool`
* `def evaluate_scope(scope: EffectiveScope, candidates: Sequence[str]) -> tuple[list[str], ScopeMatchStats]`

  * returns stable-ordered eligible list and match stats for unmatched warnings

**Key commitments:**

* Exclude wins; negated excludes are the only override.
* No Git pruning constraint: exceptions can re-include files under excluded ancestors.

---

### 2.5 `ratchetr/core/discovery.py`

**Responsibilities:**

* Discover candidate files under root given inputs and max depth
* Enforce out-of-root and symlink skipping (component-aware)
* Emit warnings and continue

**Public API:**

* `@dataclass(frozen=True) DiscoveryConfig`

  * `root: Path`
  * `max_depth: int`
* `def discover_candidates(inputs: Sequence[Path], cfg: DiscoveryConfig, warn: WarningSink) -> list[RootedPath]`

**Key commitments:**

* Return only files (not directories) as candidates.
* Stable ordering: sort output by `rel_posix`.
* Any skipped condition emits a warning event.

---

### 2.6 `ratchetr/config/scope_inputs.py` (or integrate into existing config system)

**Responsibilities:**

* Resolve effective includes/excludes using replacement precedence
* Parse env vars as JSON list only

Replacement semantics MUST treat an explicitly provided empty list (`[]`) as “provided,” replacing lower-precedence values for that list.

**Public API:**

* `@dataclass(frozen=True) ScopeInputs`

  * `includes: list[str]`
  * `excludes: list[str]`
  * `source_includes: Literal["cli","env","config","defaults"]`
  * `source_excludes: Literal["cli","env","config","defaults"]`
* `def resolve_scope_inputs(cli, env, config, defaults) -> ScopeInputs`

**Key commitments:**

* Replacement semantics for each list (includes and excludes independently).
* Env JSON parsing errors are fatal (config error class).

---

### 2.7 `ratchetr/core/outputs.py` (or extend existing output modules)

**Responsibilities:**

* Parse and normalize output destinations (`--save-as`, `--dashboard`)
* Enforce file-vs-directory intent rules
* Detect collisions and define overwrite behavior

**Public API:**

* `class OutputConfigError(ValueError)`
* `@dataclass(frozen=True) OutputTarget`

  * `format: str`  # e.g., "json", "html"
  * `path: Path`   # absolute path resolved against root (per ADR)
  * `is_dir_intent: bool`
  * `final_file: Path`  # resolved final output file path
* `def resolve_output_targets(root: Path, raw_specs: Sequence[str]) -> list[OutputTarget]`
* `def validate_no_collisions(targets: Sequence[OutputTarget]) -> None`
* `def ensure_parent_dirs(path: Path) -> None`  # should create dirs; failure is fatal
* `def write_target(target: OutputTarget, payload: bytes) -> None`  # overwrites by default

**Key commitments:**

* Relative output paths resolve against root (per ADR).
* Trailing `/` implies directory intent; file by default.
* Collisions are fatal.
* Overwrite is default.

---

### 2.8 `ratchetr/manifest/model.py` (or existing schema binding)

**Responsibilities:**

* Add warnings and (optionally) scope metadata to the manifest model

**Required model changes:**

* `warnings: list[WarningEventModel]`
* Optionally:

  * `scope: { includes_source, excludes_source, includes, excludes }`
  * `scope_unmatched_patterns: ...` (or rely purely on warnings)

**Key commitments:**

* Manifest must persist warning events from `WarningSink`.

---

### 2.9 `ratchetr/audit/runner.py` (or your existing orchestration entry point)

**Responsibilities:**

* Implement the canonical run pipeline

**Required pipeline:**

1. Resolve root
2. Resolve scope inputs (replacement precedence; env JSON)
3. Compile scope
4. Discover candidates (safety warnings collected)
5. Evaluate scope against candidates; stable order
6. Emit unmatched-pattern warnings (per policy: warn)
7. Plan engine invocation; run engines; collect results
8. Filter diagnostics to eligible set
9. Resolve output targets; validate collisions; write outputs (overwrite)
10. Write manifest including warnings

---

## 3) Algorithms and data-flow details (commitments)

### 3.1 Pattern hit tracking (for “pattern unmatched” warnings)

Implementation must decide what “matches nothing” means:

* For includes/excludes, “unmatched” refers to matching **zero discovered candidates** in that run.
* Emit a warning per unmatched pattern (or aggregate in one warning with list; either is acceptable if documented).

This requires either:

* count matches during `evaluate_scope`, or
* precompute match sets.

### 3.2 Stable ordering policy

* Discovery output sorted by `rel_posix`.
* Eligible set should preserve this order (filter in-order).
* Diagnostic sorting should be applied in a single place just before writing outputs.

### 3.3 Collision detection for outputs

Collisions must be checked against the **final resolved output file path**, not just raw strings.

Examples that should collide:

* `html:out/` and `html:out/index.html` (if `out/` implies default filename)
* repeated identical spec `json:out/report.json` twice

---

## 4) Minimal PR plan (aligned to ADR changes)

This is the recommended merge order to reduce risk:

1. Add warnings infrastructure + manifest support
2. Add canonical paths + symlink-component detection
3. Add patterns parser/matcher
4. Add scope compiler + evaluator + unmatched-pattern warnings
5. Add discovery module (safe traversal) and integrate into runner
6. Add scope input resolution with replacement precedence + env JSON parsing
7. Add outputs module (file-vs-dir intent, overwrite, collisions, mkdir)
8. Wire audit runner end-to-end with stable ordering enforced

---

## 5) Open questions explicitly resolved by ADR-000X (so they are not re-decided in code)

* Exclude wins; negated excludes are override mechanism.
* Env vars are JSON list only.
* POSIX-only separators for patterns.
* Stable ordering is required; byte-identical not required.
* Unmatched patterns produce warnings.
* `--save-as` overwrites; collisions are fatal.

---

If you share your current file structure (even a top-level `tree -L 3`), I can map this outline onto your exact modules (e.g., whether `audit/runner.py` is `cli/audit.py`, where manifest models live, whether you already have `core/path_utils.py`, etc.) so engineers get an exact “edit these files” list rather than a parallel skeleton.
