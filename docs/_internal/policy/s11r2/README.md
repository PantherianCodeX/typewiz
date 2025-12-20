# README.md — s11r2 Rewrite Governance System: Execution-Contract Workbook

**Audience:** Humans and AI agents executing the ADR/documentation rewrite using the **s11r2 execution-contract workbook**.
**Goal:** Provide an overview of the system to support a successful rewrite with **no loss**, **no drift**, and **MADR-sized ADRs**, while applying **ADR Rewrite Plan v19** deltas consistently.
**See also:** `README.md` (overview), `AGENTS.md` (full operating standards), and `QUICK_START.md` (guided workflow).
**Date:** 2025-12-19

This folder is the *operational* support package for `docs/_internal/policy/s11r2-policy.md`.

- **Humans:** use it for auditability, progress visibility, and review gates.
- **AI:** use it as the authoritative place to record “what moved where,” “what changed,” and “what still needs a decision.”

## Canonical locations

- Policy: `docs/_internal/policy/s11r2-policy.md`
- Workbook: `docs/_internal/policy/s11r2/WORKBOOK.md` (Checklists to make tracking easy)
- Registries: `docs/_internal/policy/s11r2/registers/`
- Draft-log mirrors: `docs/_internal/draft_logs/`
- Quick Start: `docs/_internal/policy/s11r2/QUICK_START.md` (Streamlined workflow to get started)
- Usage: `docs/_internal/policy/s11r2/USAGE.md` (Details about the system and how it works)
- Agents: `docs/_internal/policy/s11r2/AGENTS.md` (AI instructions for using this system)

## How to use (minimal loop)

1. Open `registers/registry_index.md` (it links to everything else).
2. Update `registers/rewrite_status.md` for the artifacts you’re actively touching.
3. Enforce ownership: update `registers/owner_index.md` before drafting.
4. Preserve draft-2 backbone:
   - add extraction items to `registers/draft2_preservation_map.md`,
   - map sources → destinations in `registers/master_mapping_ledger.md`,
   - record verbatim/adapted decisions in `registers/carry_forward_matrix.md`.
5. Apply plan-v19 deltas: log each applied delta in `registers/plan_overlay_register.md`.
6. If blocked, record it in `registers/open_questions.md` and stop.

## Editing rules (anti-drift)

- Registries are **append-first**. Prefer adding rows over rewriting history.
- Every row should include a stable source anchor (file + section/heading) and a destination.
- Avoid freeform prose in registries; use the prescribed columns.

## Recommended (low-friction) additions

- **Coherence checklist:** `docs/_internal/adr/COHERENCE_CHECKLIST.md` (run before setting Ready for review)
- **Navigation:** `external_contract_links.md` (canonical pointers; no normative restatement)
- **As-needed registries:** `registers/roadmap_register.md`, `registers/anchor_changes.md`
