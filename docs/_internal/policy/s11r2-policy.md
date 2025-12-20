# Documentation Execution Contract Policy (Rewrite Governance)

**Purpose:** Govern the ADR + supplementary-doc rewrite/migration so we (1) preserve the strongest architecture from the draft-2 ADR set, and (2) apply the deltas from **ADR Rewrite Plan v19** without duplication, drift, or scope creep.
**Status:** Normative for the rewrite effort (skeleton; to be completed by filling the referenced registries).
**Owned concepts:** rewrite governance; mapping + migration protocol; change control; registry system enforcement.
**Primary links:** `ADR Rewrite Plan v19.md` (execution plan); Draft-2 ADR set (preservation inputs); registries in `docs/_internal/policy/s11r2/`.

---

## 0. Scope and non-goals

### 0.1 In scope

- Governing policies and guardrails for rewriting ADRs and creating supplementary docs (reference specs, CLI contract docs, internal governance docs).
- Preservation protocol for draft-2 ADR architecture: taxonomy, naming, boundaries, object classes, invariants.
- Controlled overlay of ADR Rewrite Plan v19 deltas on top of preserved architecture.
- Progress visibility and mapping: sources → destinations, supersedence chain, and “what changed / why”.

### 0.2 Explicitly out of scope

- Deciding product/runtime behavior beyond what is already decided by the plan and the source ADRs/specs.
- Replacing ADR Rewrite Plan v19 (this policy *governs* how the plan is applied; it is not a rewrite-plan).
- Inventing missing technical content. Gaps must be recorded and resolved explicitly (see §7 and `open_questions.md`).

---

## 1. Authority and precedence

### 1.1 Authority order (rewrite governance)

1. This **Execution Contract Policy** (rewrite-only governance).
2. `ADR Rewrite Plan v19.md` (the execution plan and resolved deltas for the rewrite).
3. Draft-2 ADR set (architectural preservation inputs) and other existing docs *only where they do not conflict with (1) and (2)*.

### 1.2 “Stop-the-line” conditions

Work stops and a blocking entry is recorded in `open_questions.md` if any of the following occurs:

- A concept is being defined in more than one place (“one concept, one owner” violation).
- An ADR draft is expanding into inventories/grammars/default tables (MADR violation).
- A delta is applied without being recorded in `plan_overlay_register.md` (drift).
- A source-to-destination mapping cannot be demonstrated for a preserved item (loss risk).

---

## 2. Rewrite invariants (non-negotiables)

### 2.1 One concept, one owner

- Every normative concept has exactly one canonical owner document (ADR or reference spec).
- All non-owners must link to the canonical owner and may include *only* brief contextual summaries.
- Canonical ownership is tracked in:
  - `registers/owner_index.md` (primary),
  - and must remain consistent with the plan’s canonical ownership matrix.

### 2.2 ADRs stay MADR-sized

ADRs must remain decision documents:

- Context/Problem
- Decision Drivers
- Options (>=2, with acceptance/rejection rationale)
- Decision
- Consequences
- Links (to the exhaustive specs/inventories that ADRs must not contain)

### 2.3 “No inventories inside ADRs” rule

The following content classes are prohibited inside ADRs (must live in supplementary docs and be linked):

- Full grammars
- Flag inventories and applicability matrices
- Exhaustive defaults catalogs
- Exhaustive schema tables and full field-by-field definitions (unless decision-sized)

---

## 3. Document classes and boundary rules

### 3.1 Document classes

- **ADR (`docs/_internal/adr/####-*.md`)**: decision-sized, normative. Must link out for exhaustive detail.
- **Reference spec (`docs/reference/*.md`)**: normative, exhaustive, testable contracts (schemas, grammars, semantics).
- **CLI contract docs (`docs/cli/*.md`)**: user-facing inventories and contract surfaces, parity tracking.
- **Internal governance (`docs/_internal/**`)**: policies, checklists, archival, implementation notes (non-user contract).

### 3.2 Boundary enforcement

- Each ADR must have a “Must-not-contain” boundary statement aligned with the plan.
- Each supplementary doc must have tight scope and a single owning concept (or a small, explicitly-scoped cluster).
- Cross-linking is required; duplication is not.

---

## 4. Preservation protocol (draft-2 backbone)

### 4.1 Preservation mandate

The draft-2 ADR set contains strong architecture (taxonomy, naming, policy boundaries, engines) that must be preserved unless explicitly superseded by the plan.

### 4.2 Required preservation artifacts

Before rewriting any target ADR/spec, the following must be created/updated:

- `registers/draft2_preservation_map.md` — extraction map and destinations for draft-2 “backbone” items.
- `registers/master_mapping_ledger.md` — source → destination mapping at the section/concept level.
- `registers/carry_forward_matrix.md` — list of draft-2 items carried forward verbatim vs adapted, with rationale and destination.

### 4.3 No-loss rule

If a draft-2 architectural item has no mapped destination, it is treated as **lost** until mapped. The rewrite cannot advance past that gate.

---

## 5. Plan overlay protocol (v19 deltas)

### 5.1 Overlay mandate

All incoming deltas from ADR Rewrite Plan v19 must be applied *without* duplicating concepts or destabilizing preserved architecture.

### 5.2 Overlay control register

Every plan delta applied during drafting must be logged in:

- `registers/plan_overlay_register.md` — includes source anchor, decision intent, affected targets, and verification evidence.

### 5.3 Supersedence and drift control

- Known supersedences (plan overrides) are tracked in `registers/supersedence_ledger.md`.
- Any deviation from the plan must be recorded as a controlled exception in `registers/change_control.md` (with rationale and owner).

---

## 6. Mandatory traceability: headers and draft logs

### 6.1 Required header blocks (all rewritten docs)

Each rewritten ADR/spec must include a short header block after the H1:

- Purpose
- Status
- Owned concepts
- Links

(See `ADR Rewrite Plan v19.md` for the exact rule and examples.)

### 6.2 Draft logs (mirroring rule)

- Each ADR/spec maintains a concise “Draft log” section.
- Draft logs are mirrored into `docs/_internal/draft_logs/` as individual files for stable audit and review.
- If drift occurs between a doc’s draft log and the mirrored log, the rewrite is blocked until reconciled.

Templates and guidance:

- `docs/_internal/policy/s11r2/templates/draft-log-template.md`
- `docs/_internal/draft_logs/README.md`

---

## 7. Governance registries (required for the rewrite)

### 7.1 Registry system is mandatory

All rewrite work must be represented in the registries. They are the operational substrate for this policy.

Canonical location:

- `docs/_internal/policy/s11r2/`

### 7.2 Required registries (minimum set)

- `registers/registry_index.md` — navigation and canonical list (no duplicates).
- `registers/rewrite_status.md` — status of each required output artifact.
- `registers/owner_index.md` — “one concept, one owner” enforcement.
- `registers/master_mapping_ledger.md` — source → destination mapping ledger.
- `registers/draft2_preservation_map.md` — draft-2 backbone extraction and destinations.
- `registers/plan_overlay_register.md` — plan delta applications and verification.
- `registers/supersedence_ledger.md` — superseded sources and replacement pointers.
- `registers/carry_forward_matrix.md` — verbatim vs adapted carry-forward list.
- `registers/cli_parity_deltas.md` — CLI parity deltas vs help snapshots.
- `registers/terminology_map.md` — terminology/rename decisions and enforcement notes.
- `registers/open_questions.md` — blockers, ambiguities, and required decisions.
- `registers/change_control.md` — exceptions, approvals, and policy-cited deviations.
- `registers/progress_board.md` — high-level progress (phase / doc / next action).

### 7.3 Optional registries (as needed)

- `registers/roadmap_register.md` — deferred items with explicit promotion triggers
- `registers/anchor_changes.md` — anchor renames (only when anchors change)

### 7.4 Templates (recommended)

- `templates/coherence_checklist.md` — pre-review drift/duplication gate
- `external_contract_links.md` — navigation-only pointers to canonical contracts and evidence

---

## 8. Change control (anti scope-creep)

### 8.1 Allowed change types (rewrite governance only)

- Moving detail out of ADRs into reference/CLI docs, *without changing meaning*.
- Clarifying boundaries and linking to the correct owner.
- Applying plan-v19 deltas as recorded in `plan_overlay_register.md`.

### 8.2 Prohibited behaviors

- Inventing missing semantics to “fill gaps”.
- Adding new feature requirements outside plan-v19.
- Rewriting architecture (taxonomy/naming/boundaries) without mapping and explicit approval.

### 8.3 Exception protocol

Any exception requires:

- Entry in `change_control.md`,
- the affected concept mapped in `owner_index.md`,
- and a clear supersedence statement in `supersedence_ledger.md` if applicable.

---

## 9. Acceptance gates (minimum)

### 9.1 Per-ADR gate

An ADR cannot be marked “Ready for review” unless:

- Owner and boundaries are correct (per `owner_index.md` and the plan’s matrix),
- The ADR is MADR-sized and links out for detail,
- Draft log exists and is mirrored,
- All draft-2 carry-forward items assigned to that ADR are mapped and accounted for.

### 9.2 Repo-wide gate

The rewrite cannot be marked “complete” unless:

- No duplicate concept ownership exists,
- Superseded content is archived and no longer referenced,
- Terminology consistency checks pass (tracked in `terminology_map.md`),
- Parity deltas are recorded wherever the plan requires it (CLI contract vs snapshots).

---

## Appendix A. Registry schemas (tables to fill)

The registry schemas live in their respective files under:
`docs/_internal/policy/s11r2/registers/`

This policy remains intentionally concise; it is executed through those registries.

## Draft log

## 2025-12-20 — Phase 0 scaffolding

- **Change:** Established the Phase 0 policy snapshot as the rewrite governance baseline.
- **Preservation:** N/A (Phase 0 scaffolding; no draft-2 items mapped).
- **Overlay:** N/A (no Plan v19 overlays applied).
- **Mapping:** N/A (no MAP/P/CF entries yet).
- **Supersedence:** N/A.
- **Notes / risks:** None.
