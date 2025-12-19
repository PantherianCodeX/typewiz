# README.md — s11r2 Rewrite Governance System: s11r2 Progress

**Script:** `scripts/docs/build_execution_contract_progress_board.py`

This script generates the **Automated roll-up (generated)** section of the execution-contract progress board.

- **Reads:** markdown-table registries in `docs/_internal/policy/execution-contract/registers/`
- **Writes:** only the generated block in `docs/_internal/policy/execution-contract/registers/progress_board.md`

The intent is to keep rewrite tracking **mechanical and auditable**: humans maintain the source registries;
this script produces a consistent roll-up so the rewrite can be managed without missing items, duplicating concepts,
or drifting from plan-v18 overlays.

---

## Design principles

- **Stdlib only** (no external dependencies).
- **Safe edits**: the script only replaces content between:
  - `<!-- GENERATED:BEGIN -->`
  - `<!-- GENERATED:END -->`

  Everything outside these markers is preserved.
- **Audit-friendly output**: stable ordering for tables and counts. The generated block includes a timestamp;
  diffs should be limited to the timestamp and real metric changes.

---

## What it generates

Inside `progress_board.md`, the script creates:

1) **Warnings** (missing registers, missing/renamed table headers, duplicate IDs, etc.)
2) **Metric blocks** (counts/roll-ups), including:
   - Owner-index row count and ownership distribution buckets
   - Status counts for rewrite status, mapping ledger, overlay register, supersedence ledger, CLI parity deltas,
     open questions, change control
   - Preservation-map row count + posture distribution + “superseded by plan?” breakdown
   - Carry-forward posture distribution
   - Unique mapped Source IDs count

---

## Inputs and required table headers

The script searches each file for the **first markdown table** containing the required header fragments
(case-insensitive). If the headers drift, the roll-up will show a warning.

### Required registers

| Register file | Expected header fragments (must appear in the table header) |
|---|---|
| `owner_index.md` | `Concept`, `Canonical owner` |
| `rewrite_status.md` | `Artifact`, `Status` |
| `master_mapping_ledger.md` | `Row ID`, `Source ID`, `Destination doc`, `Status` |
| `draft2_preservation_map.md` | `Item ID`, `Preserve posture`, `Superseded by plan?` |
| `carry_forward_matrix.md` | `CF ID`, `Posture` |
| `plan_overlay_register.md` | `OVL ID`, `Status` |
| `supersedence_ledger.md` | `SUP ID`, `Status` |
| `cli_parity_deltas.md` | `CLI ID`, `Status` |
| `open_questions.md` | `Q ID`, `Status` |
| `change_control.md` | `CC ID`, `Status` |

### Optional registers

| Register file | Expected header fragments |
|---|---|
| `roadmap_register.md` | `ID`, `Status` |
| `anchor_changes.md` | `ID`, `Doc (path)` |

### Owner distribution buckets

The script classifies the **Canonical owner** path into buckets:
- Policy
- ADR
- Reference spec
- CLI docs
- Roadmap
- Archive
- Other

This is a lightweight “sanity check” to detect drift (e.g., too much content landing in Policy when it should
be in ADRs/specs).

---

## Usage

Run from repo root.

### Preview (prints generated block only)

```bash
python scripts/docs/build_execution_contract_progress_board.py --print
```

### Write (updates `progress_board.md` in-place)

```bash
python scripts/docs/build_execution_contract_progress_board.py --write
```

### Write and print (useful in CI logs)

```bash
python scripts/docs/build_execution_contract_progress_board.py --write --print
```

### Demo self-test (recommended when modifying the script)

```bash
python scripts/docs/build_execution_contract_progress_board.py --demo
```

The demo:
- creates a temporary copy of the registry directory,
- writes synthetic registry tables,
- generates the progress board,
- mutates inputs (e.g., changes a mapping status, adds an open question),
- regenerates and verifies the roll-up changes.

### Non-default locations

```bash
python scripts/docs/build_execution_contract_progress_board.py \
  --repo-root . \
  --register-dir docs/_internal/policy/execution-contract/registers \
  --progress-board docs/_internal/policy/execution-contract/registers/progress_board.md \
  --write
```

---

## Markdown table format requirements

- GitHub-style pipe tables are expected.
- A table must have:
  - a header row (e.g., `| ColA | ColB |`)
  - a separator row (e.g., `|---|---|`)
- **One row per line**. Multi-line cells are not supported.

---

## Troubleshooting

### The roll-up shows warnings like “Could not find … table”
- The register file exists, but the header text drifted.
- Fix by restoring the expected header fragments (see table above) or updating the script.

### The roll-up shows “Missing register: …”
- The file does not exist at the expected path.
- Either create the file (even if empty with headers) or remove it from the required set and treat it as optional.

### Duplicate mapping Row IDs warning
- `master_mapping_ledger.md` contains duplicate `Row ID` values.
- Resolve by assigning unique IDs; duplicates undermine auditability and merge safety.

---

## How to extend the roll-up safely

If you add a new register and want it reflected in the generated board:
1) Keep the register as a single, stable markdown table.
2) Add a new block in `compute_metrics()` in the script.
3) Keep the output as counts/roll-ups only (do not render full registries into the board).
4) Update `registry_index.md` so humans know the register is canonical.

---

## Recommended workflow

- Run `--write` before submitting PRs that change any register tables.
- Treat warnings in the generated roll-up as **stop-the-line** until resolved.

