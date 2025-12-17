# Ratchetr Path Scoping Contract

**Status:** Normative
**Scope:** File discovery scoping via `include` and `exclude` across CLI, environment, and config; pattern language; matching basis; override semantics; safety requirements; determinism requirements.

---

## 1) Terminology

* **Root**: The effective repository root for the run. If `--root` is provided, it is authoritative.
* **Candidate**: A file discovered (or explicitly provided) that is eligible for scoping evaluation.
* **Canonical path**: A candidate path represented as a root-relative, normalized, POSIX (`/`) path string.
* **Pattern**: A string in the ratchetr pattern language used in `include` or `exclude`.
* **Anchored pattern**: A pattern beginning with `/` that applies at the root.
* **Floating pattern**: A pattern not beginning with `/` that may match at any segment boundary.
* **Directory-only pattern**: A pattern ending with `/` that targets directories and their subtrees.
* **Negated `exclude`**: A pattern beginning with `!` in `exclude` that re-includes candidates previously excluded.

---

## 2) Inputs, sources, and precedence

### 2.1 Pattern sources

Patterns MAY be supplied via:

1. CLI
2. Environment variables
3. Configuration file
4. Defaults

### 2.2 Precedence

Precedence is: **CLI > Env > Config > Defaults**.

## 2.3 Replacement semantics

For each list independently (`include` and `exclude`), the highest-precedence source that provides a value **replaces** lower-precedence values for that list.

An explicitly provided empty list (e.g., `[]`) **counts as provided** and replaces lower-precedence values for that list.

---

## 3) Environment variables

### 3.1 Encoding

* `RATCHETR_INCLUDE` and `RATCHETR_EXCLUDE` MUST be JSON lists of strings.

  * Example: `RATCHETR_EXCLUDE='["build/","dist/","**/*.min.js"]'`

Delimiter-based encodings (comma/colon/semicolon/whitespace splitting) MUST NOT be supported.

### 3.2 Validation

* Invalid JSON or non-string list elements MUST produce a configuration error.

---

## 4) Canonical matching basis

### 4.1 Canonicalization

All matching MUST be performed against canonical paths that are:

* **Root-relative** to Root
* **Normalized** (no leading `./`, no redundant separators; `.` segments removed)
* POSIX-separated using `/`

Patterns MUST NOT be matched against absolute paths.

### 4.2 Path separator policy

* `/` is the only recognized segment separator in patterns.
* `\` has no special meaning in patterns and is treated literally.

### 4.3 Case sensitivity

Matching MUST be case-sensitive.

---

## 5) Pattern language

Patterns MAY contain arbitrary characters (including Unicode). Only the following have special meaning:

* Leading `/` — root anchoring
* Trailing `/` — directory-only subtree targeting
* `*`, `?`, `[ ... ]` — wildcard constructs within a single segment
* `**` — wildcard across segments
* Leading `!` — negation (exceptions), `exclude` **only**

All other characters are literal.

Patterns MUST be interpreted as segment-based expressions; `/` delimits segments and is not matched by `*`, `?`, or `[ ... ]`. Only `**` may match across segment boundaries.

---

## 6) Anchoring and floating

### 6.1 Root anchoring

A pattern beginning with `/` is anchored and MUST match starting at the first segment of the canonical path.

### 6.2 Floating matching

A pattern without a leading `/` is floating and MAY match starting at any segment boundary.

---

## 7) Directory-only patterns (trailing `/`)

A trailing `/` indicates directory-only semantics:

* The pattern matches directories (not files) by name and position rules (anchored vs floating).
* When a directory-only pattern matches a directory, it applies to all candidate files within that directory subtree (equivalent to matching `dir/**` for filtering files).

A directory-only pattern MUST NOT match a file of the same name.

---

## 8) Recursion and non-recursion

### 8.1 Recursive matching (`**`)

`**` matches across segment boundaries and enables recursive selection.

`**` MAY match zero segments.

### 8.2 Non-recursive directory selection (`DIR/*`)

`DIR/*` matches only immediate children of `DIR/`:

* It matches `DIR/<one-segment>` only.
* It MUST NOT match deeper descendants (`DIR/<one-segment>/<...>`).

---

## 9) Single-segment patterns (`no '/'`): literal vs wildcard

Ratchetr distinguishes single-segment patterns to support common directory selection intent while preventing wildcard patterns from unintentionally matching directory segments.

### 9.1 Single-segment literal token

A single-segment pattern with no glob metacharacters (`*`, `?`, `[`) is a literal token.

* Anchored literal (`/foo`) matches if the first segment equals `foo`.
* Floating literal (`foo`) matches if any segment equals `foo`.

Implication: a floating literal token can match a directory segment and therefore `include`/`exclude` descendants.

### 9.2 Single-segment wildcard token

A single-segment pattern containing any glob metacharacters is a wildcard token.

Wildcard tokens match **basenames only**:

* Anchored wildcard (`/*.py`) matches root-level basenames only.
* Floating wildcard (`*.py`) matches basenames at any depth.

Wildcard tokens MUST NOT match directory segments for subtree purposes.

---

## 10) Multi-segment patterns (`contains '/'`)

Multi-segment patterns are evaluated on segment boundaries.

### 10.1 Anchored multi-segment

Anchored multi-segment patterns MUST match from the first segment.

### 10.2 Floating multi-segment (suffix matching)

Floating multi-segment patterns MAY match starting at any segment boundary. For a match at a given boundary, the pattern must match the remainder of the path from that boundary, except where `**` provides explicit recursion.

---

## 11) Negation (exceptions)

### 11.1 Allowed only in `exclude`

Negation is expressed using leading `!` and is allowed only in `exclude`.

Negation in `include` MUST be rejected as a configuration error.

### 11.2 Semantics

`exclude` is evaluated in order. When an `exclude` pattern matches:

* A non-negated `exclude` sets the candidate state to excluded.
* A negated `exclude` sets the candidate state to included.

Negation is evaluated against ratchetr’s canonical candidate set and MUST NOT be constrained by Git traversal/pruning rules.

---

## 12) Inclusion algorithm

For each candidate file:

1. Base state

   * If `include` is empty: initial state is **included**.
   * If `include` is non-empty: initial state is **excluded**.

2. Apply `include` (if any)

   * If `include` is non-empty, a candidate becomes included if it matches **any** include pattern.

3. Apply `exclude` (ordered)

   * Evaluate excludes in order, updating inclusion state:

     * match `exclude` → excluded
     * match negated `exclude` → included

The final state determines whether the candidate is in scope.

**Precedence rule:** `exclude` is applied after `include`; `exclude` therefore wins by default, and negated `exclude` provides the explicit override mechanism.

---

## 13) Warnings for unmatched patterns

Ratchetr MUST emit a warning and record it in the manifest when a **user-supplied** include or exclude pattern matches **no candidates** for the run (after discovery).

* “User-supplied” means: patterns sourced from **CLI, environment variables, or configuration file**.
* Defaults do not participate in unmatched-pattern warning evaluation.

This warning is non-fatal.

---

## 14) Discovery safety requirements

### 14.1 Out-of-root

Any input or discovered candidate that resolves outside Root MUST be:

* skipped
* warned
* recorded in the manifest as a structured warning event

### 14.2 Symlinks

Symlink traversal is disabled. Any input or discovered candidate that is:

* a symlink, or
* contains any symlink component between Root and the candidate
  MUST be:
* skipped
* warned
* recorded in the manifest as a structured warning event

Processing MUST continue after these warnings.

### 14.3 Minimum warning fields

Warnings recorded in the manifest MUST include at least:

* `code`
* `severity` (warning)
* `message`
* `action` (skipped or info)
* `root`
* `path_input` (if applicable)
* `path_resolved` (best-effort, if available)
* `pattern` (if applicable)

---

## 15) Determinism requirements

Ratchetr MUST provide stable ordering for:

* discovered candidate files (by canonical `rel_posix`)
* scoped eligible file lists
* diagnostics emitted in manifest and dashboards
* manifest and dashboard section ordering
* warnings recorded in the manifest

Warnings MUST be recorded in **emission order**.

Byte-identical artifacts are not required.

---

## 16) Shell expansion guidance

Users SHOULD quote patterns in shells that expand globs. Ratchetr treats the received strings literally and does not attempt to detect or reverse shell expansion.
