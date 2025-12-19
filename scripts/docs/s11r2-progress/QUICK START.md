# QUICK_START.md — s11r2 Rewrite Governance System: s11r2 Progress

This folder contains small, deterministic helpers that generate audit-friendly roll-ups
for the documentation rewrite.

## Execution-contract progress board

Generates the **automated roll-up** section in:

- `docs/_internal/policy/execution-contract/registers/progress_board.md`

from the markdown-table registries in:

- `docs/_internal/policy/execution-contract/registers/`

### Run
From repo root:

```bash
python scripts/docs/build_execution_contract_progress_board.py --write
```

Preview output without writing:

```bash
python scripts/docs/build_execution_contract_progress_board.py --print
```

### Demo self-test

```bash
python scripts/docs/build_execution_contract_progress_board.py --demo
```

The demo runs on a temporary copy and verifies that changing input tables changes the
roll-up, to reduce the chance of “silent stale dashboards”.
