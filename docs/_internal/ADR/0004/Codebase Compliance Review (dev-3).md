# Codebase Compliance Review (dev-3)

The following items are **noncompliant with this taxonomy** and should be corrected. These are structural/taxonomy issues only.

1. **Unit test directories do not consistently mirror product domains**

   * **Observed (dev-3):** `tests/unit/misc/`, `tests/unit/models/`, `tests/unit/utilities/`; and `tests/unit/common/test_paths.py` testing non-`common` modules.
   * **Impact:** Violates the “mirror product domains” rule; makes placement subjective and encourages drift (tests become “wherever they fit” rather than “where they belong”).
   * **Correction:** Relocate tests into domain-aligned paths (e.g., `tests/unit/core/`, `tests/unit/_internal/`, `tests/unit/paths/` or `tests/unit/runtime/` depending on what they’re testing). If you want meta/guardrail tests, introduce a narrowly-scoped `tests/unit/architecture/` and keep it minimal.

2. **Builders and other test-code utilities are misclassified as fixtures**

   * **Observed (dev-3):** Python modules living under `tests/fixtures/` (e.g., `tests/fixtures/builders.py`, helper modules, and snapshot/stub Python modules).
   * **Impact:** Breaks the fixture/data vs helper/code taxonomy; `tests/fixtures/` becomes a mixed-purpose bucket and is likely to accrete more code over time.
   * **Correction:** Move builder/factory code into `tests/helpers/builders/` (or `tests/helpers/builders.py`), and move fake implementations/assertion helpers into `tests/helpers/fakes/` and `tests/helpers/assertions/`. Keep `tests/fixtures/` for data artifacts only (including `tests/fixtures/snapshots/`).

3. **Unit tests for non-runtime repository tooling lack an explicit taxonomy exception**

   * **Observed (dev-3):** `tests/unit/scripts/` exists, but `scripts/` is a repository tooling area (non-runtime by taxonomy).
   * **Impact:** “Unit mirrors runtime domains” becomes ambiguous if repo-tooling tests are mixed into the same mirroring scheme without an explicit exception.
   * **Correction:**

     * Move these into a dedicated top-level suite like `tests/scripts/`

4. **Root package contains substantive implementation (`ratchetr/json.py`)**

   * **Observed (alpha-3):** `src/ratchetr/json.py` defines JSON types and multiple helper functions and normalization logic (implementation, not façade).
   * **Impact:** Violates the strict façade rule; expands public surface unintentionally and encourages additional “generic helpers” at the root.
   * **Correction (strict façade):**

     * Move implementation to `_internal/utils/json.py` (or a more specific private namespace under `_internal/` if preferred).
     * Replace `ratchetr/json.py` with either:

       * **Removal** (preferred if JSON helpers are not intended public), updating internal imports accordingly; or
       * A **thin façade** that re-exports a deliberately chosen subset with `__all__` (only if you explicitly want a public JSON helper surface).

5. **Root façade module set must be intentionally minimal (review required)**

   * **Observed (alpha-3 root modules):** `api.py`, `cache.py`, `collections.py`, `error_codes.py`, `exceptions.py`, `json.py`, `logging.py`, `paths.py`, `precedence.py`, `runtime.py`, plus `__init__.py`, `__main__.py`.
   * **Impact:** Even if each is a façade, excessive façade modules dilute the “single obvious public API” and increase maintenance overhead.
   * **Correction:** For each root module, classify it as:

     * **Entrypoint** (`__main__.py`),
     * **Canonical public API aggregator** (`__init__.py`),
     * **Intentional stable sub-entrypoint** (keep as façade), or
     * **Nonessential convenience façade** (remove and keep functionality internal; re-export via `__init__` only if needed).
     * Under strict façade, *nonessential convenience façades should be eliminated*.

6. **Root façade imports must not depend on non-façade root implementations**

   * **Observed risk (alpha-3):** `runtime.py` re-exports JSON helpers by importing from `ratchetr.json` (which is currently an implementation module).
   * **Impact:** Root façade modules must not be layered on top of other root implementation modules; it hides implementation and complicates future refactors.
   * **Correction:** After moving JSON implementation behind `_internal/`, ensure root façades import from `_internal/*` or feature packages directly, not from other root implementation modules.
