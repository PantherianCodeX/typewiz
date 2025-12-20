# s11r2 progress outputs (generated)

This directory contains **generated** progress artifacts for the s11r2 rewrite governance system.

- `progress_board.md` is generated from the canonical registries under `../registers/`.
- `dashboard/index.html` is a generated static HTML view of the same roll-ups.

Do not hand-edit files in this directory. Edit the source registries and rerun:

- `python scripts/docs/s11r2-progress.py --write`
- `python scripts/docs/s11r2-progress.py --write --write-html`
