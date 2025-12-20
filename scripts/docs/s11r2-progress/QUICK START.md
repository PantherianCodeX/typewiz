# Quick Start: s11r2 progress outputs

From the repo root:

```bash
python scripts/docs/s11r2-progress.py --write --write-html
```

This will:

- Read `docs/_internal/policy/s11r2/registers/registry_index.md`
- Validate governance tables using status codes from `STATUS_LEGEND.md`
- Write the generated outputs to the paths declared in the registry index (by default under `docs/_internal/policy/s11r2/progress/`)

If you only want one output:

- Markdown only: `python scripts/docs/s11r2-progress.py --write`
- HTML only: `python scripts/docs/s11r2-progress.py --write-html`
- Auto-update (long-running, dashboard only): `python scripts/docs/s11r2-progress.py --auto-update --update-interval 10`
- Auto-update markdown only: `python scripts/docs/s11r2-progress.py --auto-update --update-interval 10 --write`
- Auto-update markdown + dashboard: `python scripts/docs/s11r2-progress.py --auto-update --update-interval 10 --write --write-html`

## CI / gating mode

```bash
python scripts/docs/s11r2-progress.py --check --fail-on WARN
```

- Fails if the generated outputs are missing or out of date.
- Fails if any issues at or above the configured threshold are detected.
