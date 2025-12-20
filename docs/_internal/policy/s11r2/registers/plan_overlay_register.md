# Plan overlay register (ADR Rewrite Plan v19 deltas)

Every applied plan delta must be logged here before it is considered “done”. This is the primary drift-control ledger.

**Status codes:** see `STATUS_LEGEND.md`.

| OVL ID | Plan anchor (section/heading) | Delta summary (one line) | Affected targets (docs) | Ownership impact? (Y/N) | Evidence (link/commit/PR) | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OVL-0001 | §1.3.1 POSIX path semantics | Enforce POSIX-only path contract posture in ADR-0006 + path_resolution | `docs/_internal/adr/0006-paths-foundation.md`, `docs/reference/path_resolution.md` | N | TBD | RV | Cite policy snapshot in ADR |
| OVL-0002 | §1.2 Formal run artifacts mandatory | Require run artifacts set + disclosure even when persistence suppressed | `docs/_internal/adr/0003-execution-contract-foundation.md`, `docs/reference/run_artifacts.md` | N | TBD | RV | Align with artifact vs persistence rule |
| OVL-0003 | §7.1 Engine errors minimum surface | Define engine error schema and state stderr is never diagnostics | `docs/reference/engine_errors.md` | N | TBD | RV | Required in Phase 2 acceptance |
| OVL-0004 | §1.2 Resolution happens once | Resolution immutability; no re-discovery in planning/execution | `docs/_internal/adr/0003-execution-contract-foundation.md` | N | TBD | RV | Resolution→Plan→Run immutability |
