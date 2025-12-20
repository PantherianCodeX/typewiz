# AGENTS.md — s11r2 Rewrite Governance System

**Audience:** AI agents contributing to the ADR + documentation rewrite under the **s11r2 execution-contract workbook**.
**Primary purpose:** Ensure the rewrite succeeds **without loss, drift, duplication, or bloat**, while cleanly applying **ADR Rewrite Plan v19** deltas on top of preserved draft-2 architecture.
**See also:** `README.md` (overview), `QUICK_START.md` (guided workflow), and `USAGE.md` (in-depth).
**Date:** 2025-12-19

---

## 0. Before you write anything: required context load

You must understand the system **before drafting**. The minimum required reading order is:

1. `docs/_internal/policy/s11r2-policy.md` (rewrite governance policy; not the full product spec)
2. `docs/_internal/policy/s11r2/README.md` (how the workbook/registries are used)
3. `docs/_internal/policy/s11r2/registers/registry_index.md` (canonical registry list)
4. `docs/_internal/policy/s11r2/WORKBOOK.md` (the operational loop)
5. `ADR Rewrite Plan v19.md` (execution plan and authoritative rewrite deltas)
6. Draft-2 ADR inputs (as needed for the doc you are touching)

If any of these files are missing in your working tree, **stop** and record a blocker in:
`docs/_internal/policy/s11r2/registers/open_questions.md`.

### 0.1 Precision-safe extraction (avoid UI truncation)

**ATTENTION:** Use these patterns instead of relying on rendered views:

**Shell-first:**

- `grep -n -- '<token>' <file>`
- `nl -ba <file> | sed -n '<start>,<end>p'`

**Python line-by-line (never “bare display”):**

```python
for ln, txt in lines:
    print(f"{ln:04d}: {txt}")
```

Never use ellipses (`...`) as omission markers in normative text.

---

## 1. Authority, scope, and “stop-the-line”

### 1.1 Authority order (do not invert)

1. `docs/_internal/policy/s11r2-policy.md` (governance for the rewrite)
2. `ADR Rewrite Plan v19.md` (execution plan + resolved deltas)
3. Draft-2 ADR set (preservation inputs, unless explicitly superseded)

### 1.2 Hard scope constraints (non-negotiable)

- This effort rewrites **documents**, not product runtime behavior.
- Do **not** invent new requirements or semantics to “fill gaps.”
- ADRs must remain **MADR-sized** decision documents; exhaustive detail belongs in reference/CLI docs.
- The registries are mandatory. If it is not recorded, it does not exist.

### 1.3 Stop-the-line conditions

Stop drafting and create/update an entry in `registers/open_questions.md` when any of the following occur:

- A concept is being defined in more than one place (**one concept, one owner** violation).
- A draft is turning into inventories/grammars/default tables (**ADR bloat**).
- A plan delta is being applied without being recorded in `registers/plan_overlay_register.md`.
- A preserved draft-2 item has no mapped destination (**loss risk**).
- You cannot provide stable evidence for a claim or mapping row.

---

## 2. The operating system (workbook + registries)

### 2.1 Canonical locations (s11r2)

- Governance policy: `docs/_internal/policy/s11r2-policy.md`
- Workbook: `docs/_internal/policy/s11r2/WORKBOOK.md`
- Registries (canonical): `docs/_internal/policy/s11r2/registers/`
- Draft-log mirrors: `docs/_internal/draft_logs/`
- Templates: `docs/_internal/policy/s11r2/templates/`

### 2.2 Canonical registries (what each is for)

Use `registers/registry_index.md` as the canonical list. You will most commonly update:

- `rewrite_status.md` — what you are working on, next action, blockers
- `owner_index.md` — **one concept, one owner** (define owners before drafting)
- `master_mapping_ledger.md` — source→destination mapping (section/concept level) with evidence
- `draft2_preservation_map.md` — extracted draft-2 backbone items + destinations
- `carry_forward_matrix.md` — verbatim vs adapted carry-forward decisions + rationale
- `plan_overlay_register.md` — applied Plan v19 deltas + verification evidence
- `supersedence_ledger.md` — superseded content and pointers/replacements
- `cli_parity_deltas.md` — help snapshot vs contract deltas (tracking only; help is not policy)
- `terminology_map.md` — vocabulary decisions/renames and enforcement notes
- `change_control.md` — explicit exceptions/amendments to governance
- `anchor_changes.md` — record anchor renames (only when anchors change)

---

## 3. Required workflow (do this every time)

This is the minimum compliant loop. Do not “draft first, reconcile later.”

### 3.1 Start of session

1. Pick a target artifact (ADR/spec/CLI doc/policy/gov doc).
2. Update `registers/rewrite_status.md`:
   - set status to **In progress**
   - set **Next action**
   - link any known blockers (Q-IDs)
3. Confirm or establish ownership in `registers/owner_index.md` for every concept you expect to touch.

### 3.2 Preservation + mapping gate (before drafting)

1. Extract relevant draft-2 items → `registers/draft2_preservation_map.md`
2. Map source→destination → `registers/master_mapping_ledger.md`
3. Decide carry-forward posture (verbatim/adapted/superseded/deferred) → `registers/carry_forward_matrix.md`

If you cannot map it, it is considered **lost** until mapped. Do not proceed.

### 3.3 Overlay gate (while drafting)

For each applied Plan v19 delta:

1. Record it in `registers/plan_overlay_register.md` (source anchor → targets → evidence)
2. If it supersedes older content, update `registers/supersedence_ledger.md`

### 3.4 Draft log + mirror gate

1. Add a concise entry to the doc’s **Draft log** section.
2. Mirror that entry into `docs/_internal/draft_logs/<doc-id>.md` (see template)
3. If the mirror and the doc drift, treat as a blocker (Q-entry).

### 3.5 Ready-for-review gate

Before marking a doc ready:

- Run `templates/coherence_checklist.md`
- Update `rewrite_status.md` → **Ready for review**
- Ensure every rule you touched points to a single owner and has evidence in registries

---

## 4. Drafting standards (high rigor, low bloat)

### 4.1 ADR format must be MADR (literal headings)

Each ADR must contain the MADR headings as **literal** headings:

- Context/Problem
- Decision Drivers
- Considered Options
- Decision Outcome
- Consequences
- Links

No bespoke ADR formats unless the plan/policy explicitly allows it and you record the exception in `change_control.md`.

### 4.2 ADR “must-not-contain” rule (strict)

ADRs must **not** include:

- inventories or applicability matrices (flags, defaults, engines, etc.)
- full grammars
- schema field tables / exhaustive object catalogs
- long lists of rules better expressed in reference specs

Instead, ADRs must link to the canonical owner spec(s).

### 4.3 Ownership discipline

- Define the owner before you define or restate anything normative.
- Non-owners may include only a short orientation and a link to the owner.
- Never create “shadow policy” in a plan, registry, or workbook.

### 4.4 Terminology discipline

- All term renames must be recorded in `terminology_map.md`.
- If you change an anchor, record it in `anchor_changes.md` immediately.

---

## 5. Evidence and precision (no truncation, no ambiguity)

### 5.1 Evidence requirements

Registry rows must include evidence as:

- `path#anchor` references
- CLI help snapshot references (file + line ranges)
- precise extraction commands (see below)

## 6. Project tracking: how “done” is defined

### 6.1 Progress is tracked in registries

- The canonical progress tracker is `registers/rewrite_status.md`.
- Progress outputs are generated from the registries (do not hand-edit files under `progress/`).
- Regenerate after registry edits: `python scripts/docs/s11r2-progress.py --write --write-html`.

### 6.2 Completion gates (minimum)

A doc cannot be “Done/Approved” unless:

- Ownership is correct (`owner_index.md`)
- Draft-2 carry-forward mapping is complete for impacted items
- Plan overlays are logged and evidenced
- Supersedence pointers exist where needed
- Draft log + mirror are consistent

---

## 7. Quality bars for any scripts/tooling you add

This rewrite is document-focused, but minimal doc-control tooling may exist. If you must modify or introduce a helper script:

- Prefer **no external dependencies**.
- Deterministic output (stable ordering).
- Clear CLI usage and safe defaults.
- Python: type hints + docstrings; avoid cleverness; include a dry-run option if destructive.
- Add a short note in `change_control.md` if the script changes governance workflow.

If you are not certain the script is necessary, record an Open Question rather than adding tooling.

---

## 8. Common failure modes (avoid these)

- Writing an ADR that reads like a spec (bloat).
- Creating a second mapping table “just for convenience” (duplicate truth).
- Applying a plan delta without logging it (silent drift).
- Moving content without a supersedence pointer (broken migration trail).
- Renaming anchors without recording (citation breakage).
- “Fixing” missing semantics by invention (policy violation).

---

## 9. Quickstart: one compliant work cycle (example)

1. Set target: ADR-0003 rewrite.
2. Update `rewrite_status.md` → ADR-0003 = In progress, next action “extract draft-2 boundaries invariants”.
3. Update `owner_index.md` for boundary semantics owners.
4. Populate:
   - `draft2_preservation_map.md` with boundary/layering invariants
   - `master_mapping_ledger.md` mapping draft-2 sections → new ADR + reference specs
   - `carry_forward_matrix.md` marking verbatim/adapted decisions
5. Draft ADR using literal MADR headings; link out to the reference specs.
6. Log plan deltas in `plan_overlay_register.md` with evidence.
7. Add draft log entry + mirror file under `docs/_internal/draft_logs/ADR-0003.md`.
8. Run `templates/coherence_checklist.md`.
9. Update `rewrite_status.md` → Ready for review.

---

## 10. Where to ask for decisions

If you need a decision that is not already resolved by the plan/policy:

- Record it as a blocking entry in `registers/open_questions.md`
- Include at least two options and the affected artifacts
- Do not proceed until it is resolved and recorded
