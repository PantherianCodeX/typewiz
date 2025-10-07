# typewiz Dashboard

- Generated at: 2025-01-01T00:00:00Z
- Project root: `/repo`

## Overview

- Errors: 4
- Warnings: 2
- Information: 1

### Run summary

| Run | Errors | Warnings | Information | Command |
| --- | ---: | ---: | ---: | --- |
| `pyright:current` | 3 | 2 | 1 | `pyright --outputjson` |
| `mypy:full` | 1 | 0 | 0 | `python -m mypy` |

### Engine details

#### `pyright:current`
- Profile: baseline
- Config file: pyrightconfig.json
- Plugin args: `--lib`
- Include paths: `apps`
- Exclude paths: `apps/legacy`
- Folder overrides:
  - `apps/platform` (plugin args: `--warnings`)

#### `mypy:full`
- Profile: strict
- Config file: mypy.ini
- Plugin args: `--strict`
- Include paths: `packages`
- Exclude paths: —
- Folder overrides:
  - `packages/legacy` (exclude: `packages/legacy`)

### Hotspots

#### Diagnostic rules

| Rule | Count |
| --- | ---: |
| `reportUnknownMemberType` | 2 |
| `reportGeneralTypeIssues` | 1 |

#### Folder hotspots

| Folder | Errors | Warnings | Information | Runs |
| --- | ---: | ---: | ---: | ---: |
| `apps/platform/operations` | 2 | 1 | 0 | 2 |
| `packages/agents` | 1 | 1 | 0 | 1 |

#### File hotspots

| File | Errors | Warnings |
| --- | ---: | ---: |
| `apps/platform/operations/admin.py` | 2 | 0 |
| `packages/core/agents.py` | 1 | 1 |

### Run logs

#### `pyright:current`
- Errors: 3
- Warnings: 2
- Information: 1
- Total diagnostics: 6
- Severity breakdown: {}

#### `mypy:full`
- Errors: 1
- Warnings: 0
- Information: 0
- Total diagnostics: 1
- Severity breakdown: {}
