# QUICK_START.md — s11r2 Rewrite Governance System

**Audience:** Humans and AI agents executing the ADR/documentation rewrite using the **s11r2 execution-contract workbook**.
**This file:** A **quickstart** to begin work safely and consistently.
**See also:** `README.md` (overview), `AGENTS.md` (full operating standards), and `USAGE.md` (in-depth).
**Date:** 2025-12-19

---

## 1) Start here (5–10 minutes)

### 1.1 Open these files in this order

1. `docs/_internal/policy/s11r2-policy.md`
2. `docs/_internal/policy/s11r2/WORKBOOK.md`
3. `docs/_internal/policy/s11r2/registers/registry_index.md`
4. `docs/_internal/policy/s11r2/registers/rewrite_status.md`

If any are missing, **stop** and record a blocker in:
`docs/_internal/policy/s11r2/registers/open_questions.md`.

---

## 2) The minimal compliant loop (do this every time)

### Step A — Declare the work item (2 minutes)

Update `registers/rewrite_status.md`:

- set the target document row to **IP**
- fill **Next action**
- if anything is unclear, set **BL** and reference a Q-ID from `open_questions.md`

**Rule:** If it’s not in `rewrite_status.md`, it’s not “in progress.”

---

### Step B — Confirm “one concept, one owner” (2–5 minutes)

Before writing any normative statement, confirm ownership:

- update `registers/owner_index.md` for concepts you will touch
- each owner must be `path#anchor`

**Stop-the-line:** if two documents already define the same concept, record an Open Question and pause.

---

### Step C — Map draft-2 → destination (mandatory gate)

Record the preservation and mapping trail **before drafting**:

1. `registers/draft2_preservation_map.md`
   - extract the relevant draft-2 invariants/objects/terms
2. `registers/master_mapping_ledger.md`
   - map each extracted item to a destination owner (`path#anchor`)
   - include **evidence**
3. `registers/carry_forward_matrix.md`
   - record disposition: **PRESERVE | RELOCATE | SUPERSEDE | DEFER**
   - cite policy/plan anchors

**Rule:** Unmapped items are treated as **at risk of loss**. Do not proceed.

---

### Step D — Apply Plan v18 overlays (as you draft)

For every Plan v18 delta you apply:

- record it in `registers/plan_overlay_register.md` with evidence
- if it replaces older content, add a row to `registers/supersedence_ledger.md`

---

### Step E — Draft and log (keep ADRs MADR-sized)

- Draft the target document.
- ADRs must remain decision-sized (no inventories/grammars/schema catalogs/default tables).
- Add a draft log entry in-doc and mirror to:
  - `docs/_internal/draft_logs/<doc-id>.md` (**must** use template)

---

### Step F — Gate for review and completion

Run `templates/coherence_checklist.md` and then:

- set status to **RV** (ready for review) or **DN** (done) in `rewrite_status.md`
- confirm every touched concept is owned and every preserved/delta item is mapped with evidence

---

## 3) “Stop-the-line” triggers (do not push through)

Create/update a row in `open_questions.md` and mark impacted docs **BL** when:

- ownership is ambiguous (duplicate normativity)
- a draft-2 item has no destination mapping
- a plan overlay is being applied without a registry entry
- an ADR is growing into spec territory (bloat risk)
- you cannot provide a stable anchor + evidence for a claim

---

## 4) Evidence discipline (avoid UI truncation)

Registries must cite evidence via:

- `path#anchor`, or
- snapshot filename + line range, or
- precise extraction command.

**Shell-first:**

- `grep -n -- '<token>' <file>`
- `nl -ba <file> | sed -n '<start>,<end>p'`

**Python line-by-line:**

```python
for ln, txt in lines:
    print(f"{ln:04d}: {txt}")
```

Never use ellipses (`...`) as omission markers in normative text.

---

## 5) Quick reference: “Where do I record this?”

| Task | Record in |
| --- | --- |
| Define/change a concept | `owner_index.md` (+ `terminology_map.md` if wording/term changes) |
| Preserve/move draft-2 content | `draft2_preservation_map.md` + `master_mapping_ledger.md` + `carry_forward_matrix.md` |
| Apply Plan v18 delta | `plan_overlay_register.md` (+ `supersedence_ledger.md` if replacing) |
| CLI contract vs help/code delta | `cli_parity_deltas.md` |
| Exception to governance | `change_control.md` |
| Anchor rename | `anchor_changes.md` |
| Blocker/ambiguity | `open_questions.md` + mark `rewrite_status.md` as BL |

---

## 6) Confirm README alignment (maintenance note)

This Quickstart intentionally avoids duplicating overview content.
If `README.md` is updated, keep the following division:

- `README.md`: what this system is + directory layout + where to start
- `Quickstart`: the minimal compliant loop + stop-the-line triggers
- `AGENTS.md`: full standards and anti-drift discipline
