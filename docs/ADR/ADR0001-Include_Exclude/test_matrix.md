# Test Matrix: Path Scoping, Pattern Semantics, Safety, and Determinism

**Status:** Normative test plan
**Scope:** Verifies the Path Scoping Contract end-to-end via (1) pure matcher tests, (2) pure scope evaluation tests, (3) filesystem-backed discovery safety tests, and (4) determinism tests.
**Conventions:** All candidate paths in matcher/scope suites are **canonical root-relative POSIX** paths.

---

## 0) Suite structure and required test harnesses

### 0.1 Matcher suite (pure)

Validates: `matches(pattern, candidate_rel_posix) -> bool`

### 0.2 Scope suite (pure)

Validates: `in_scope(includes, excludes, candidate_rel_posix) -> bool`
Also validates ordered exclude evaluation and negation behavior.

### 0.3 Discovery safety suite (filesystem-backed)

Validates:

* canonicalization to root-relative POSIX
* out-of-root skip + warning + manifest record
* symlink skip (leaf and component) + warning + manifest record
* traversal continues after warnings
* stable ordering of discovered candidates

### 0.4 Determinism suite (mixed)

Validates stable ordering of:

* candidate lists
* eligible lists
* diagnostics ordering inputs (via sorting rules; may be unit-tested on synthetic diagnostics)

---

## 1) Matcher Suite (pure)

Each case:

* `id`
* `pattern`
* `candidate`
* `expected`

### 1.1 Root anchoring (`/`)

**M-ANCH-001:**

* pattern: `/src/**`
* candidate: `src/pkg/a.py`
* expected: `true`

**M-ANCH-002:**

* pattern: `/src/**`
* candidate: `other/src/pkg/a.py`
* expected: `false`

**M-ANCH-003:**

* pattern: `/foo` (single-seg literal, anchored)
* candidate: `foo/bar.py`
* expected: `true`

**M-ANCH-004:**

* pattern: `/foo`
* candidate: `src/foo/bar.py`
* expected: `false`

### 1.2 Floating multi-segment matching (may start at any boundary)

**M-FLOAT-001:**

* pattern: `tests/**`
* candidate: `tests/unit/test_a.py`
* expected: `true`

**M-FLOAT-002:**

* pattern: `tests/**`
* candidate: `src/tests/unit/test_a.py`
* expected: `true`

**M-FLOAT-003:**

* pattern: `tests/**`
* candidate: `src/testsuite/unit/test_a.py`
* expected: `false`

### 1.3 Single-segment literal tokens (segment match)

**M-LIT-001:**

* pattern: `foo`
* candidate: `src/foo/bar.py`
* expected: `true` (segment `foo` present)

**M-LIT-002:**

* pattern: `foo`
* candidate: `src/pkg/foo`
* expected: `true` (basename equals `foo`)

**M-LIT-003:**

* pattern: `foo`
* candidate: `src/pkg/foobar.py`
* expected: `false`

**M-LIT-004:**

* pattern: `/foo`
* candidate: `foo`
* expected: `true`

**M-LIT-005:**

* pattern: `/foo`
* candidate: `foo/bar/baz.py`
* expected: `true`

### 1.4 Single-segment wildcard tokens (basename-only)

**M-WILD-001:**

* pattern: `*.py`
* candidate: `src/a.py`
* expected: `true`

**M-WILD-002:**

* pattern: `*.py`
* candidate: `src/dir.py/file.txt`
* expected: `false` (basename is `file.txt`)

**M-WILD-003:**

* pattern: `*.py`
* candidate: `src/dir.py/file.py`
* expected: `true`

**M-WILD-004:**

* pattern: `/*.py`
* candidate: `a.py`
* expected: `true`

**M-WILD-005:**

* pattern: `/*.py`
* candidate: `src/a.py`
* expected: `false`

**M-WILD-006:**

* pattern: `?.py`
* candidate: `a.py`
* expected: `true`

**M-WILD-007:**

* pattern: `?.py`
* candidate: `ab.py`
* expected: `false`

**M-WILD-008:**

* pattern: `[ab].py`
* candidate: `b.py`
* expected: `true`

### 1.5 Multi-segment patterns without recursion (exact remainder match)

**M-SUFF-001:**

* pattern: `foo/bar`
* candidate: `src/foo/bar`
* expected: `true`

**M-SUFF-002:**

* pattern: `foo/bar`
* candidate: `src/foo/bar/baz.py`
* expected: `false`

**M-SUFF-003:**

* pattern: `/foo/bar`
* candidate: `foo/bar`
* expected: `true`

**M-SUFF-004:**

* pattern: `/foo/bar`
* candidate: `src/foo/bar`
* expected: `false`

### 1.6 Recursive `**`

**M-STARSTAR-001:**

* pattern: `foo/**`
* candidate: `src/foo/bar/baz.py`
* expected: `true`

**M-STARSTAR-002:**

* pattern: `foo/**`
* candidate: `src/foobar/baz.py`
* expected: `false`

**M-STARSTAR-003:**

* pattern: `/src/**`
* candidate: `src/a.py`
* expected: `true`

### 1.7 Directory-only (`/` trailing)

**M-DIR-001:**

* pattern: `build/`
* candidate: `src/build/out.json`
* expected: `true`

**M-DIR-002:**

* pattern: `/build/`
* candidate: `src/build/out.json`
* expected: `false`

**M-DIR-003:**

* pattern: `/build/`
* candidate: `build/out.json`
* expected: `true`

**M-DIR-004:**

* pattern: `build/`
* candidate: `build` (file candidate)
* expected: `false`

### 1.8 Non-recursive directory selection (`DIR/*`)

**M-NR-001:**

* pattern: `/src/*`
* candidate: `src/a.py`
* expected: `true`

**M-NR-002:**

* pattern: `/src/*`
* candidate: `src/pkg/a.py`
* expected: `false`

**M-NR-003:**

* pattern: `tests/*`
* candidate: `src/tests/test_a.py`
* expected: `true`

**M-NR-004:**

* pattern: `tests/*`
* candidate: `src/tests/unit/test_a.py`
* expected: `false`

### 1.9 Separator policy (POSIX-only)

**M-SEP-001:**

* pattern: `src\**`
* candidate: `src/a.py`
* expected: `false` (backslash is literal, not a separator)

**M-SEP-002:**

* pattern: `src\pkg\file.py`
* candidate: `src/pkg/file.py`
* expected: `false` (literal backslashes do not match `/` separators)

### 1.10 Case sensitivity

**M-CASE-001:**

* pattern: `Src/**`
* candidate: `src/a.py`
* expected: `false`

---

## 2) Scope Suite (pure)

Each case:

* `id`
* `includes`
* `excludes`
* `candidate`
* `expected`

### 2.1 Base behavior (empty includes = include-all)

**S-BASE-001:**

* includes: `[]`
* excludes: `[]`
* candidate: `src/a.py`
* expected: `true`

**S-BASE-002:**

* includes: `[]`
* excludes: [`build/`]
* candidate: `src/build/out.json`
* expected: `false`

### 2.2 Whitelist mode (non-empty includes)

**S-WL-001:**

* includes: [`/src/**`]
* excludes: `[]`
* candidate: `src/a.py`
* expected: `true`

**S-WL-002:**

* includes: [`/src/**`]
* excludes: `[]`
* candidate: `tests/test_a.py`
* expected: `false`

### 2.3 Excludes win; negated excludes override

**S-OVR-001:**

* includes: [`/src/**`]
* excludes: [`tests/`]
* candidate: `src/tests/test_a.py`
* expected: `false`

**S-OVR-002:**

* includes: [`/src/**`]
* excludes: [`tests/`, `!src/tests/keep.py`]
* candidate: `src/tests/keep.py`
* expected: `true`

### 2.4 Re-include under excluded ancestor (ratchetr-friendly)

**S-NEG-001:**

* includes: `[]`
* excludes: [`generated/`, `!generated/keep.py`]
* candidate: `generated/keep.py`
* expected: `true`

**S-NEG-002:**

* includes: `[]`
* excludes: [`generated/`, `!generated/sub/keep.py`]
* candidate: `generated/sub/keep.py`
* expected: `true`

**S-NEG-003:**

* includes: `[]`
* excludes: [`generated/`, `!generated/keep.py`, `generated/keep.py`]
* candidate: `generated/keep.py`
* expected: `false` (later rule wins)

### 2.5 Literal token subtree include + directory-only exclusion

**S-LITDIR-001:**

* includes: [`foo`]
* excludes: [`foo/`]
* candidate: `foo` (file)
* expected: `true`

**S-LITDIR-002:**

* includes: [`foo`]
* excludes: [`foo/`]
* candidate: `src/foo/bar.py`
* expected: `false`

### 2.6 Non-recursive directory selection in includes

**S-NR-001:**

* includes: [`/src/*`]
* excludes: `[]`
* candidate: `src/a.py`
* expected: `true`

**S-NR-002:**

* includes: [`/src/*`]
* excludes: `[]`
* candidate: `src/pkg/a.py`
* expected: `false`

### 2.7 Invalid configuration cases (must error)

These are validation tests; expected outcome is a configuration error.

**S-ERR-001:**

* includes: [`!/src/**`]
* excludes: `[]`
* expected: configuration error (negation not allowed in includes)

**S-ERR-002:**

* includes: [`!foo`]
* excludes: `[]`
* expected: configuration error

**S-ERR-003:**

* includes: [`/`] or an empty/invalid pattern token
* excludes: `[]`
* expected: configuration error

---

## 3) Discovery Safety Suite (filesystem-backed)

Each case asserts:

* candidates produced (canonical `rel_posix`)
* warnings emitted (and recorded for manifest)
* stable ordering of candidates

### 3.1 Out-of-root input skipped + warning

**D-OOR-001:**

* root: `<tmp>/repo`
* input: `<tmp>/secrets.txt` (outside root)
* expected candidates: `[]`
* expected warning:

  * code: `PATH_OUTSIDE_ROOT`
  * action: `skipped`
  * root present
  * path_input present
  * path_resolved best-effort

**D-OOR-002:**

* root: `<tmp>/repo`
* input: `../secrets.txt` (relative out-of-root)
* expected candidates: `[]`
* expected warning:

  * code: `PATH_OUTSIDE_ROOT`
  * action: `skipped`
  * root present
  * path_input present
  * path_resolved best-effort

### 3.2 Symlink leaf skipped + warning

**D-SYM-001:**

* root: `<tmp>/repo`
* setup: `repo/src/link` is a symlink (target arbitrary)
* input: `src/link`
* expected candidates: `[]`
* expected warning:

  * code: `SYMLINK_SKIPPED`
  * action: `skipped`

### 3.3 Symlink component skipped + warning

**D-SYM-002:**

* root: `<tmp>/repo`
* setup:

  * `repo/src/linkdir` is a symlink
  * user input attempts `src/linkdir/file.py`
* input: `src/linkdir/file.py`
* expected candidates: `[]`
* expected warning: `SYMLINK_SKIPPED`

### 3.4 Discovery continues after warnings

**D-CONT-001:**

* root: `<tmp>/repo`
* setup:

  * valid file `src/a.py`
  * symlink `src/link`
  * out-of-root input `../secrets.txt` (or absolute)
* inputs: `[src/a.py, src/link, ../secrets.txt]`
* expected candidates: [`src/a.py`]
* expected warnings: both `SYMLINK_SKIPPED` and `PATH_OUTSIDE_ROOT`

### 3.5 Canonicalization normalization

**D-NORM-001:**

* root: `<tmp>/repo`
* setup: file exists at `src/pkg/a.py`
* input: `./src/./pkg//a.py`
* expected candidates: [`src/pkg/a.py`]

### 3.6 Stable ordering of discovered candidates

**D-ORD-001:**

* root: `<tmp>/repo`
* setup files:

  * `b/b.py`
  * `a/a.py`
  * `a/z.py`
* input: root directory
* expected candidates order: [`a/a.py`, `a/z.py`, `b/b.py`] (lexicographic by rel_posix)

---

## 4) Unmatched Pattern Warnings Suite (mixed)

These tests validate that patterns matching zero discovered candidates produce warnings (non-fatal) recorded in the manifest.

### 4.1 Unmatched include warning

**U-PAT-001:**

* discovered candidates: [`src/a.py`]
* includes: [`/does-not-exist/**`]
* excludes: `[]`
* expected eligible: `[]`
* expected warning:

  * code: `PATTERN_UNMATCHED`
  * pattern: `/does-not-exist/**`
  * source: scope/config (implementation choice, but must be present)

### 4.2 Unmatched exclude warning

**U-PAT-002:**

* discovered candidates: [`src/a.py`]
* includes: `[]`
* excludes: [`generated/`]
* expected eligible: [`src/a.py`]
* expected warning:

  * code: `PATTERN_UNMATCHED`
  * pattern: `generated/`

### 4.3 Matched patterns must not warn

**U-PAT-003:**

* discovered candidates: [`src/a.py`]
* includes: [`/src/**`]
* excludes: [`build/`]
* expected eligible: [`src/a.py`]
* expected warnings:
  * `PATTERN_UNMATCHED` for `build/` only

---

## 5) Determinism Suite (mixed)

These tests ensure stable ordering obligations are met.

### 5.1 Stable eligible list ordering

**R-ORD-001:**

* discovered candidates (unsorted input): [`b/b.py`, `a/z.py`, `a/a.py`]
* includes: `[]`
* excludes: `[]`
* expected eligible order: [`a/a.py`, `a/z.py`, `b/b.py`]

### 5.2 Stable diagnostics ordering

Define a canonical sort for diagnostics (at minimum):
`rel_posix`, `line`, `column`, `code`, `message`.

**R-DIAG-001:**

* input diagnostics (unsorted):

  * `src/b.py:10:1 E100 ...`
  * `src/a.py:2:5 E200 ...`
  * `src/a.py:2:1 E100 ...`
* expected output order:

  1. `src/a.py:2:1 E100 ...`
  2. `src/a.py:2:5 E200 ...`
  3. `src/b.py:10:1 E100 ...`

### 5.3 Stable manifest section ordering

If manifest is composed of sections (e.g., engines, results, warnings), assert a stable order for keys/arrays. At minimum:

* warnings array should be stable ordered by `(code, pattern/path_input, message)` or insertion order (choose one and enforce it).

**R-MAN-001:**

* given deterministic inputs and traversal, warnings are emitted in a known order:
  1. discovery-time warnings (out-of-root, symlink) in the order encountered, then
  2. unmatched-pattern warnings in deterministic pattern order
* expected manifest warnings order: **exactly the emission order**

---

## 6) Precedence and Env Parsing Suite (unit-level)

### 6.1 Replacement precedence (includes/excludes independently)

**P-REP-001:**

* defaults includes: `[]`
* config includes: [`/src/**`]
* env includes: [`/tests/**`]
* cli includes: not provided
* expected effective includes: [`/tests/**`] (env replaces config/defaults)

**P-REP-002:**

* defaults excludes: [`build/`]
* config excludes: [`dist/`]
* env excludes: not provided
* cli excludes: [`generated/`]
* expected effective excludes: [`generated/`] (cli replaces)

**P-REP-003:**

* defaults includes: [`/src/**`]
* config includes: [`/tests/**`]
* env includes: `[]` (explicit empty list)
* cli includes: not provided
* expected effective includes: `[]` (env replaces)

**P-REP-004:**

* defaults excludes: [`build/`]
* config excludes: [`dist/`]
* env excludes: not provided
* cli excludes: `[]` (explicit empty list)
* expected effective excludes: `[]` (cli replaces)

### 6.2 Env JSON parsing validation

**P-ENV-001:**

* env: `RATCHETR_EXCLUDES='["build/","dist/"]'`
* expected: parsed list of strings

**P-ENV-002:**

* env: `RATCHETR_EXCLUDES='{"build/": true}'`
* expected: configuration error (not a JSON list)

**P-ENV-003:**

* env: `RATCHETR_EXCLUDES='["build/", 123]'`
* expected: configuration error (non-string element)

---

## 7) Acceptance coverage checklist

This matrix verifies:

* Canonical root-relative POSIX matching basis
* POSIX-only separator policy for patterns
* Anchored vs floating semantics
* Directory-only patterns and subtree effect
* `**` recursion semantics
* `DIR/*` non-recursive semantics
* Literal single-segment segment matching (including directory segment inclusion)
* Wildcard single-segment basename-only matching
* Exclude precedence with negated excludes as override mechanism
* Ordered exclude evaluation
* Invalid negation in includes
* Out-of-root and symlink skip behavior with warnings and manifest logging
* Unmatched pattern warnings
* Stable ordering requirements
* Replacement precedence for scope inputs
* Env vars as JSON list only
