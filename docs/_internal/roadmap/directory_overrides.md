# Roadmap: directory overrides (deferred; non-normative)

**Owner(s):** ADR-0009 + ADR-0002.

**Status:** Stub created in Phase 0. Directory-level configuration overlays are intentionally deferred; this file captures a promotable design outline only.

**Source:** `docs/_internal/ADR Rewrite Plan v19.md` §5.8.

---

## 1. Contract posture (today)

- Directory-level configuration overlays are **not** specified as normative behavior in the ADR/reference set until the core contract stabilizes.
- If any overlay behavior exists in the current implementation, treat it as **non-normative parity-only** (record it as a parity delta) and do not let it shape normative ADR wording.

---

## 2. Forward-compatibility requirements (must be preserved now)

Even while overlays are deferred, the core specs must remain overlay-ready:

- ADR-0002 (planning) and ADR-0009 (config) must preserve **overlay-ready plan identity** invariants so overlays can be introduced later without breaking plan equivalence and dedupe semantics.

Minimum plan-identity dimensions to preserve:

- effective scope segment(s) being executed
- effective config inputs used to derive behavior (source-resolved, not raw)
- relevant resolution dimensions that affect engine behavior (e.g., follow mode, allow-absolute gating)

---

## 3. Design capture (to be expanded before promotion)

This section is a placeholder outline; populate it before any policy-driven promotion.

### 3.1 Discovery boundaries

Define:

- what constitutes an “overlay”
- where overlay discovery is permitted
- how overlays interact with Project vs Ad-hoc Mode

### 3.2 Partitioning strategy

Define how a single requested scope partitions into multiple plan invocations when overlays are active.

### 3.3 Plan identity + dedupe invariants

Define:

- identity dimensions (effective scope segments + effective config inputs + relevant resolution dimensions)
- canonicalization rules used for dedupe/equivalence
- invariants that must remain stable across versions

### 3.4 Follow/boundary interactions

Capture interactions with:

- follow modes (ADR-0008)
- link traversal beyond base/project boundaries
- boundary counts and disclosures

### 3.5 Conflict and precedence narratives

Capture how overlays relate to existing precedence layers:

- CLI overrides
- ENV overrides (when enabled)
- base config discovery/loading
