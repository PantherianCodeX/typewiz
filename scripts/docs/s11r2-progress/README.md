# s11r2 progress generator

This tooling generates the **s11r2 governance monitoring outputs** from the register set under:

- `docs/_internal/policy/s11r2/registers/`

## Outputs

The generator emits:

- **Progress board (markdown)** — intended for repo viewing and markdown linting
- **Monitoring dashboard (HTML)** — intended for quick situational awareness

**Output paths are discovered from** `docs/_internal/policy/s11r2/registers/registry_index.md`.
This keeps filenames/locations configurable without hard-coding them into the script.

By default, the registry index points to:

- `docs/_internal/policy/s11r2/progress/progress_board.md`
- `docs/_internal/policy/s11r2/progress/dashboard/index.html`

## Status codes and validation

All governance tables that use a `Status` (or `Current status`) column are expected to use the
**status code set defined in** `STATUS_LEGEND.md`.

The generator:

- Loads allowed status codes from `STATUS_LEGEND.md`.
- Validates status codes in the core governance tables.
- Emits issues with one of these severities: `ERROR`, `WARN`, `INFO`.
- Generates outputs even when issues exist, so you can see the report.
- Exits non-zero when the configured failure threshold is met.

## Usage

From repo root:

```bash
python scripts/docs/s11r2-progress.py --write --write-html
```

Common modes:

- Write both markdown + HTML outputs:
  ```bash
  python scripts/docs/s11r2-progress.py --write --write-html
  ```
- Only write markdown:
  ```bash
  python scripts/docs/s11r2-progress.py --write
  ```
- Only write HTML:
  ```bash
  python scripts/docs/s11r2-progress.py --write-html
  ```
- Validate that generated outputs are up-to-date (CI-friendly):
  ```bash
  python scripts/docs/s11r2-progress.py --check --fail-on WARN
  ```

Exit codes:

- `0` — success
- `1` — generated outputs are missing or out of date (`--check` mode)
- `2` — issues detected at or above the configured failure threshold

## Notes

- **Do not hand-edit generated outputs.** Edit the registers, then regenerate.
- **No manual roll-up is used.** Progress is computed from the register set under
  `docs/_internal/policy/s11r2/registers/`.
