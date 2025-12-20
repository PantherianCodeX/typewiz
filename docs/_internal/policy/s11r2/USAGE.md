# USAGE.md — s11r2 Rewrite Governance System

**Audience:** Humans and AI agents executing the ADR/documentation rewrite using the **s11r2 execution-contract workbook**.
**Goal:** Ensure a successful rewrite with **no loss**, **no drift**, and **MADR-sized ADRs**, while applying **ADR Rewrite Plan v19** deltas consistently.
**See also:** `README.md` (overview), `AGENTS.md` (full operating standards), and `QUICK_START.md` (guided workflow).
**Date:** 2025-12-19

---

## 1. What this system is

s11r2 is a **rewrite governance and recording system**. It provides:

- a workbook workflow (`WORKBOOK.md`) that defines the working loop,
- a set of registries (`registers/`) that provide **the canonical record** of:
  - ownership (“one concept, one owner”),
  - mapping (draft-2 → rewritten destinations),
  - overlay decisions (Plan v19 deltas),
  - supersedence pointers (migration trace),
  - blockers (open questions),
  - progress and gating.

This system is designed to be:

- **easy to audit**, and
- **safe to run with AI agents**.

It is not a runtime spec.

---

## 2. Directory layout (canonical)

Within `docs/_internal/policy/s11r2/`:

- `README.md` — overview
- `WORKBOOK.md` — operational loop (the “how we work” document)
- `registers/` — canonical registries (single source of truth)
- `templates/` — checklists + draft log templates

---

## 3. Core concepts (minimal vocabulary)

- **Owner:** the single canonical document + anchor that defines a concept/rule/schema/surface.
- **Registry:** a tracking document that records mapping/progress/decisions without restating specs.
- **Disposition:** how a draft-2 concept is treated: PRESERVE | RELOCATE | SUPERSEDE | DEFER.
- **Overlay decision:** a Plan v19 delta applied during the rewrite.
- **Stop-the-line:** when something is ambiguous or conflicting, record it and pause.

---

## 4. The minimal compliant workflow

### 4.1 Start a work item (required)

1. Choose a target artifact (ADR/spec/CLI doc).
2. Update `registers/rewrite_status.md`:
   - status = IP (in progress)
   - next action
   - known blockers (Q-IDs)

### 4.2 Establish ownership (required)

Before writing normative statements:

- add/update `registers/owner_index.md` for the concepts you will touch,
- ensure the owner includes `path#anchor`.

### 4.3 Map draft-2 to destinations (required)

1. Extract draft-2 items into `registers/draft2_preservation_map.md`.
2. Map source→destination into `registers/master_mapping_ledger.md` (must include evidence).
3. Record disposition and rationale in `registers/carry_forward_matrix.md`.

If you cannot map a concept, it is treated as **at risk of loss**. Stop and create an Open Question.

### 4.4 Apply plan overlays (required)

For every Plan v19 delta you apply:

- record it in `registers/plan_overlay_register.md`,
- add verification evidence (path#anchor or snapshot/line range),
- update `registers/supersedence_ledger.md` if anything is replaced.

### 4.5 Draft and log (required)

- Draft the target doc (ADRs must be MADR-sized; see §5).
- Add a draft log entry in the doc.
- Mirror the entry into `docs/_internal/draft_logs/<doc-id>.md` using the template.

### 4.6 Gate for review (required)

- Run `templates/coherence_checklist.md`.
- Update `rewrite_status.md` to RV (in review).
- Ensure registry rows are complete and have evidence.

### 4.7 Mark done (required)

A doc may be marked DN only if:

- owners exist,
- mappings and dispositions are recorded,
- overlays are recorded,
- supersedence is recorded where needed,
- blockers are resolved or explicitly deferred.

---

## 5. ADR-specific drafting rules (MADR + anti-bloat)

ADRs must:

- use MADR headings as **literal headings**,
- remain decision-sized,
- link out to reference specs for detail,
- avoid inventories, grammars, schema field catalogs, and default tables.

If an ADR starts accumulating detailed tables, move them to:

- `docs/reference/*` (normative specs) or
- `docs/cli/*` (contract surfaces)

Record the move in the registries (mapping + supersedence if needed).

---

## 6. Precision and evidence (non-negotiable)

### 6.1 Evidence in registries

For each mapping/overlay/delta row, include:

- `path#anchor` references, or
- CLI help snapshot file + line ranges, or
- exact extraction commands.

### 6.2 Precision-safe extraction (avoid UI truncation)

**Shell-first:**

- `grep -n -- '<token>' <file>`
- `nl -ba <file> | sed -n '<start>,<end>p'`

**Python line-by-line:**

```python
for ln, txt in lines:
    print(f"{ln:04d}: {txt}")
```

Do not rely on rendered views for long files. Do not use ellipses as omission markers in normative text.

---

## 7. Registry cheat sheet (what to update)

| You are doing… | Update these registries |
| --- | --- |
| Defining or changing a concept/rule/schema/surface | `owner_index.md`, `terminology_map.md` |
| Preserving/moving/superseding draft-2 content | `draft2_preservation_map.md`, `master_mapping_ledger.md`, `carry_forward_matrix.md`, `supersedence_ledger.md` |
| Applying Plan v19 deltas | `plan_overlay_register.md`, (often) `delta_register.md` |
| Tracking CLI contract mismatches | `cli_parity_deltas.md` |
| Hitting ambiguity/conflict | `open_questions.md`, then mark docs BL in `rewrite_status.md` |
| Making an exception/amendment | `change_control.md` |
| Changing anchors | `anchor_changes.md` |
| Updating progress | `rewrite_status.md` (then regenerate progress outputs) |

---

## 8. Troubleshooting (common issues)

- **You can’t find where a rule belongs:** check `owner_index.md`. If missing, create an entry and assign an owner.
- **Draft-2 item has no destination:** add to `open_questions.md` and do not proceed.
- **Two docs restate the same normativity:** pick a canonical owner and replace the other with a link; record in mapping + supersedence.
- **An ADR is too long:** move details to a reference spec; keep ADR decision-sized.

---

## 9. Quickstart checklist (copy/paste)

- [ ] Update `rewrite_status.md` → IP + next action
- [ ] Confirm owners in `owner_index.md`
- [ ] Extract to `draft2_preservation_map.md`
- [ ] Map to `master_mapping_ledger.md` (with evidence)
- [ ] Record disposition in `carry_forward_matrix.md`
- [ ] Record overlays in `plan_overlay_register.md` (with evidence)
- [ ] Draft doc (MADR-sized ADRs)
- [ ] Add draft log + mirror file
- [ ] Run coherence checklist
- [ ] Mark RV or DN in `rewrite_status.md`
