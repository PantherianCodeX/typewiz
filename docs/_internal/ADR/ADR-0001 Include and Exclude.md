# ADR-0001: Path Scoping, Pattern Semantics, Safety Boundaries, Determinism, and Output Path Resolution

**Status:** Accepted
**Date:** 2025-12-13
**Owners:** Ratchetr maintainers
**Scope:** How ratchetr discovers and scopes files for scanning (`include`/`exclude`), the pattern language and matching basis, safety boundaries (out-of-root, symlinks), determinism requirements, and output path resolution for `--save-as` / `--dashboard`.

---

## 1. Context

Ratchetr needs a predictable, cross-platform mechanism to select files for scanning. Users expect familiar, glob-like expressions for `include` and `exclude`, while ratchetr must remain safe by construction (never scanning outside the configured root or traversing symlinks) and usable at scale (very large repos).

The project also aims to minimize long-term runtime dependencies; therefore, relying on external gitignore parsers (e.g., `pathspec`) or adopting full Git ignore semantics is not preferred if a simpler, ratchetr-owned contract can meet requirements.

In parallel, output destinations (manifests/dashboards) must have consistent and unambiguous path resolution rules to avoid surprising behavior and to make automation reliable.

---

## 2. Decision Summary

Ratchetr will:

1. Implement a **ratchetr-defined, glob-like pattern language** for `include` and `exclude` (not full gitignore semantics, not stdlib glob semantics “as the contract”).
2. Match patterns against **root-relative, normalized POSIX paths** (using `/` separators). **Backslash (`\`) is not supported as a path separator in patterns** in v1.
3. Support:

   * root anchoring via leading `/`
   * floating matches otherwise
   * directory-only patterns via trailing `/`
   * recursion via `**`
   * non-recursive directory selection via `DIR/*`
   * negation (`!pattern`) **only in `exclude`** as the mechanism to override excludes
4. Apply the **include/exclude algorithm** such that:

   * if `include` is empty, baseline is include-all
   * if `include` are non-empty, baseline is whitelist-only
   * `exclude` is applied after `include`, in order
   * `exclude` matches win over `include` matches, except where overridden by **negated** ``exclude``
5. Enforce safety:

   * **out-of-root**: skip, warn, and record in manifest
   * **symlink traversal**: never traverse; if a path is a symlink or contains any symlink component under root, skip, warn, and record in manifest
6. Require **stable ordering** (deterministic ordering) for traversal outputs and emitted artifacts; byte-identical output is not required.
7. Standardize scalable engine input planning modes (response file / stdin list / argv batching / tool globs / tool-root scoped / full-root fallback) and require ratchetr to remain the semantic authority by filtering diagnostics to the canonical scoped file set.
8. For outputs (`--save-as`, `--dashboard`): treat output targets as **files by default**, overwrite existing output files, and use explicit rules to avoid file/directory ambiguity.

---

## 3. Detailed Decisions

### 3.1 Canonical matching basis

All matching is performed against a canonical path representation:

* **root-relative** to the effective repo root (`--root` is authoritative)
* **normalized** (no `./`, no redundant separators)
* **POSIX separators** (`/`) only

Patterns are **never** matched against absolute paths.

**Rationale:** This produces stable, portable matching semantics independent of OS-specific path conventions. It also avoids ambiguity around drive letters and platform-dependent separators.

---

### 3.2 Configuration sources and precedence

`include` and `exclude` may be provided via:

1. CLI
2. Environment variables
3. Config file
4. Defaults

**Precedence:** CLI > Env > Config > Defaults.

**List replacement rule (simplicity-first):** For each of `include` and `exclude`, the highest-precedence source that provides a value **replaces** lower-precedence values for that list.

**Explicit empty lists:** An explicitly provided empty list (e.g., `[]`) **counts as provided** and therefore replaces lower-precedence values for that list.

**Rationale:** Replacement avoids surprising “hidden” patterns inherited from lower layers and keeps the mental model simple when troubleshooting.

---

### 3.3 Environment variable encoding

* `RATCHETR_INCLUDE` and `RATCHETR_EXCLUDE` are **JSON lists of strings** (only).

  * Example: `RATCHETR_EXCLUDE='["build/","dist/","**/*.min.js"]'`

No delimiter-based encoding (comma/colon/semicolon) is supported in v1.

**Rationale:** JSON lists are unambiguous, avoid OS-dependent thinking, and avoid delimiter conflicts with pattern characters.

---

### 3.4 Pattern language

Patterns apply in both `include` and `exclude`, with the exception that negation is allowed only in `exclude`.

#### 3.4.1 Metacharacters

Patterns may contain arbitrary characters; only the following have special meaning:

* Leading `/` → root-anchored
* Trailing `/` → directory-only (subtree)
* `*`, `?`, `[ ... ]` → single-segment wildcards
* `**` → multi-segment wildcard (crosses `/`)
* Leading `!` → negation (`exclude` **only**)

All other characters are literal.

#### 3.4.2 Separator policy (POSIX-only)

* `/` is the only recognized segment separator in patterns.
* `\` is treated as a literal character in patterns (no special handling).

**Rationale:** This keeps the contract OS-agnostic and avoids introducing cross-platform ambiguity in config files. Windows-style copy/paste convenience is deferred.

#### 3.4.3 Anchoring and floating

* **Anchored** patterns begin with `/` and match starting at root.
* **Floating** patterns have no leading `/` and may match starting at any segment boundary.

#### 3.4.4 Directory-only patterns (trailing `/`)

A trailing `/` indicates directory-only matching:

* It matches directories (not files).
* When it matches, it applies to all descendants (subtree semantics).

This enables excluding directory subtrees without excluding a file of the same name.

#### 3.4.5 Non-recursive directory selection (`DIR/*`)

`DIR/*` matches only immediate children of `DIR/` and does not match grandchildren or deeper descendants.

This is the preferred way to express “scan this folder without recursion,” complemented by the global `max_depth` discovery control.

#### 3.4.6 Recursion (`**`)

`**` matches across segment boundaries and enables recursive selection:

* `foo/**` matches any depth under `foo/`
* `**` may match zero segments (e.g., `/src/**` matches `/src/a.py`)

#### 3.4.7 Single-segment semantics (literal vs wildcard)

To support common user intent while avoiding surprising subtree matches:

* **Single-segment literal tokens** (no `*`, `?`, `[`) match **any path segment**:

  * anchored `/foo`: first segment is `foo`
  * floating `foo`: any segment is `foo`
  * consequence: `foo` can match a directory segment and `include` descendants
* **Single-segment wildcard tokens** (contain `*`, `?`, `[`) match **basenames only**:

  * anchored `/*.py`: root-level basenames only
  * floating `*.py`: basenames at any depth

**Rationale:** Users expect `foo` to be usable as “the folder named foo,” while they generally expect `*.py` to mean “python files,” not “anything under a directory whose name happens to match `*.py`.”

#### 3.4.8 Case sensitivity

Matching is **case-sensitive** at the contract level.

**Rationale:** This prevents platform-dependent behavior and keeps outputs stable across environments.

---

### 3.5 Include/exclude evaluation and negation

#### 3.5.1 Baseline inclusion

* If `include` is empty: baseline is **included**.
* If `include` is non-empty: baseline is **excluded** unless matched by at least one `include`.

#### 3.5.2 Exclude and overrides

* `exclude` is applied **after** `include`, in the order provided.
* A matching `exclude` sets the candidate to excluded.
* A matching **negated `exclude`** (`!pattern`) sets the candidate to included.

**Precedence rule:** `exclude` wins over include by default; **negated `exclude` are the explicit override mechanism**.

**Negation constraint:** Negation is allowed **only** in `exclude`. Negation in `include` is a configuration error.

**Rationale:** This provides a single, explicit override mechanism while avoiding Git’s traversal/pruning constraints and avoiding a more complex precedence model.

---

### 3.6 Warnings for unmatched “non-existent” patterns

Ratchetr emits an informational warning (and records it in the manifest) when a **user-supplied** include or exclude pattern matches **no discovered candidates** for the run.

* “User-supplied” means: patterns sourced from **CLI, environment, or config**.
* Defaults do not participate in unmatched-pattern warning evaluation.

These warnings are non-fatal.

**Rationale:** Users requested visibility into patterns that have no effect (commonly due to typos, moved paths, or incorrect anchoring), while still allowing patterns intended for generated files or future changes.

---

### 3.7 Discovery behavior and depth

* Ratchetr discovers candidate files under root from:

  * explicit user inputs (positional paths), and/or
  * default discovery roots (as defined by the CLI command)
* Directory traversal is recursive by default, constrained by `max_depth` (existing control).
* “Non-recursive directory scanning” is expressed via patterns (`DIR/*`) rather than requiring a special per-include recursion flag.

**Rationale:** This avoids introducing an additional recursion toggle in the contract while still providing precise control.

---

### 3.8 Safety boundaries and manifest logging

#### 3.8.1 Out-of-root

Any path that resolves outside root is:

* skipped
* warned to the user
* recorded in the manifest as a structured warning event

#### 3.8.2 Symlinks

Symlink traversal is disabled. Any path that:

* is itself a symlink, or
* contains any symlink component between root and the candidate

is skipped, warned, and recorded in the manifest.

Processing continues after warnings.

**Rationale:** This prevents unintended scope expansion and makes skipped scope explicit and auditable, which is important for CI and compliance-oriented use cases.

---

### 3.9 Engine input planning and scalability

Ratchetr standardizes engine input modes (plugins choose the best supported option), prioritizing performance:

1. Response-file (`@paths.txt`) style
2. Stdin list
3. Batched argv list
4. Tool-native globs (plugin responsibility to maintain safety)
5. Tool-root scoped via tool config/exclude
6. Full tool-root (fallback)

**Correctness invariant:** Ratchetr computes the canonical in-scope file set and filters diagnostics to it, regardless of how a tool was invoked.

**Rationale:** This avoids requiring plugins to perfectly translate ratchetr semantics into each tool’s glob language for correctness while still enabling performance-oriented invocation strategies.

---

### 3.10 Determinism and ordering

Ratchetr provides stable ordering for:

* discovered candidate file lists (canonical `rel_posix` ordering)
* scoped eligible file lists
* diagnostics emitted in manifest and dashboards
* manifest and dashboard section ordering
* warnings recorded in the manifest

Warnings are recorded in **emission order**. Emission must be deterministic given stable discovery traversal and stable scope evaluation.

Byte-identical artifacts are not required; timestamps may be present.

**Rationale:** Stable ordering is sufficient for review, CI, and reproducibility without imposing restrictions that complicate normal operation.

---

### 3.11 Output path resolution (`--save-as` / `--dashboard`)

#### 3.11.1 File vs directory intent

* Output targets are treated as **files by default**.
* A trailing `/` explicitly indicates a **directory intent** (e.g., `out/`).

#### 3.11.2 Overwrite policy

When `--save-as` or `--dashboard` is used, ratchetr will **overwrite existing output files** by default.

(Configurability may be added later; v1 favors simplicity.)

#### 3.11.3 Collisions

If the same output destination is specified more than once in a single command invocation and would result in multiple writers targeting the same final path, ratchetr will treat this as a **collision error** (fatal) with a clear message identifying the conflicting outputs.

**Rationale:** Silent last-wins or deduplication can hide configuration mistakes; explicit failure makes CI behavior predictable.

---

## 4. Alternatives Considered

### 4.1 Full gitignore semantics

Rejected due to complexity, Git traversal/pruning corner rules that are not aligned with checker workflows, and the likely need for external dependencies to be correct.

### 4.2 Stdlib glob/fnmatch/pathlib “as the contract”

Rejected due to inconsistent expectations and API differences; ratchetr requires a single coherent contract.

### 4.3 OS-dependent environment parsing (pathsep delimiters)

Rejected because it makes configuration dependent on OS conventions; JSON list encoding is unambiguous and portable.

### 4.4 Backslash-as-separator support

Deferred. Supporting Windows-style `\` separators in patterns is convenient for copy/paste but introduces cross-platform ambiguity and additional escape rules. v1 remains POSIX-only for separators.

### 4.5 “Explicit `include` overrides `exclude`”

Rejected. The chosen model is “`exclude` wins; negated `exclude` provides explicit exceptions,” which is simpler and maps directly to the requested override mechanism.

---

## 5. Consequences

### Positive outcomes

* Portable, deterministic scoping contract that is owned and testable within ratchetr.
* Clear, auditable safety posture (no out-of-root, no symlink traversal) with manifest visibility.
* Practical non-recursive directory selection (`DIR/*`) without expanding the CLI surface.
* Scalable engine invocation planning without compromising correctness.

### Tradeoffs

* Windows users must use `/` in patterns (for now).
* Some Git ignore expectations will not carry over (intentionally).
* Replacement semantics for precedence reduce “implicit merging” flexibility, but simplify debugging and CI consistency.

---

## 6. Follow-ups and Deferred Items

* Optional support for `\` as a separator (would require explicit escaping rules to preserve correctness on POSIX).
* Optional `--force` / “no-overwrite” policies for outputs.
* Optional `--deterministic` / “no timestamps” mode for byte-identical manifests if needed later.
* Optional additional warning categories (e.g., duplicates) if user feedback suggests value.

---
