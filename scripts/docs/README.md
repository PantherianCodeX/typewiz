# README.md — s11r2 Rewrite Governance System: Script Support

This folder contains small, deterministic helpers that generate audit-friendly roll-ups
for the documentation rewrite.

## Execution-contract progress board

Generates the **automated roll-up** section in:

- `docs/_internal/s11r2/registers/progress_board.md`

from the markdown-table registries in:

- `docs/_internal/s11r2/registers/`

### Run
From repo root:

```bash
python scripts/docs/s11r2-progress.py --write
```

Preview output without writing:

```bash
python scripts/docs/s11r2-progress.py --print
```

### Demo self-test

```bash
python scripts/docs/s11r2-progress.py --demo
```

The demo runs on a temporary copy and verifies that changing input tables changes the
roll-up, to reduce the chance of “silent stale dashboards”.
