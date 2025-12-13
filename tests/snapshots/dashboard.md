# ratchetr Dashboard

- Generated at: 2025-01-01T00:00:00Z
- Project root: `/repo`

## Overview

- Errors: 1
- Warnings: 1
- Information: 0

## Run summary

| Run | Errors | Warnings | Information | Command |
| --- | ---: | ---: | ---: | --- |
| `pyright:current` | 0 | 0 | 0 | `pyright --outputjson` |
| `mypy:full` | 1 | 1 | 0 | `python -m mypy` |

## Engine details

### `pyright:current`

- Profile: baseline
- Config file: pyrightconfig.json
- Plugin args: `--lib`
- Include paths: `apps`
- Exclude paths: `apps/legacy`
- Folder overrides:
  - `apps/platform` (plugin args: `--warnings`)

### `mypy:full`

- Profile: strict
- Config file: mypy.ini
- Plugin args: `--strict`
- Include paths: `packages`
- Exclude paths: —
- Folder overrides:
  - `packages/legacy` (exclude: `packages/legacy`)

## Hotspots

### Diagnostic rules

| Rule | Count |
| --- | ---: |
| `reportUnknownMemberType` | 1 |
| `reportGeneralTypeIssues` | 1 |

### Rule hotspots by file

- `reportGeneralTypeIssues`: `packages/core/agents.py` (1)
- `reportUnknownMemberType`: `packages/core/agents.py` (1)

### Folder hotspots

| Folder | Errors | Warnings | Information | Runs |
| --- | ---: | ---: | ---: | ---: |
| `apps/platform/operations` | 0 | 0 | 0 | 1 |
| `packages/agents` | 1 | 1 | 0 | 1 |

### File hotspots

| File | Errors | Warnings |
| --- | ---: | ---: |
| `apps/platform/operations/admin.py` | 0 | 0 |
| `packages/core/agents.py` | 1 | 1 |

## Run logs

### `pyright:current`

- Errors: 0
- Warnings: 0
- Information: 0
- Total diagnostics: 0
- Severity breakdown: {}

### `mypy:full`

- Errors: 1
- Warnings: 1
- Information: 0
- Total diagnostics: 2
- Severity breakdown: {}

## Readiness snapshot

- Ready for strict typing: `apps/platform/operations`
- Close to strict typing: `packages/agents`
- Blocked folders: —

### Per-option readiness

- **Unknown type checks** (≤2 to be close):
  - Ready: `apps/platform/operations`
  - Close: `packages/agents`
  - Blocked: —
- **Optional member checks** (≤2 to be close):
  - Ready: `apps/platform/operations`
  - Close: —
  - Blocked: —
- **Unused symbol warnings** (≤4 to be close):
  - Ready: `apps/platform/operations`
  - Close: —
  - Blocked: —
- **General diagnostics** (≤5 to be close):
  - Ready: `apps/platform/operations`
  - Close: —
  - Blocked: —
