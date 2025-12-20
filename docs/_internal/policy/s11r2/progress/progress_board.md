# s11r2 progress board

## Generated

Timestamp: 2025-12-20T04:15:53+00:00

This file is generated from the canonical s11r2 registries. Edit source registries under `../registers/`, then regenerate progress outputs.

## Links

- Registry index: [../registers/registry_index.md](../registers/registry_index.md)
- Status legend: [../registers/STATUS_LEGEND.md](../registers/STATUS_LEGEND.md)
- Dashboard: [dashboard/index.html](dashboard/index.html)

## Regeneration

Run from repo root:

- `python scripts/docs/s11r2-progress.py --write`
- `python scripts/docs/s11r2-progress.py --write --write-html`

<!-- GENERATED:BEGIN s11r2-progress -->

## Generated monitoring

### Validation findings

- Errors: 0
- Warnings: 0
- Info: 0

### Status legend

|Code|Label|Meaning|
|---|---|---|
|NS|Not Started|Question logged, but no real investigation begun.|
|IP|In Progress|Actively investigating; sources are being consulted and options refined.|
|RV|In Review|Proposed resolution exists and is awaiting maintainer decision / review gate.|
|DN|Done|Decision made and recorded (with a stable reference), and work is unblocked.|
|BL|Blocked|Work cannot proceed (or must not proceed) until this is resolved.|

### Derived metrics

#### Operational snapshot

|Metric|Value|
|---|---:|
|Indexed registries (markdown)|14|
|Registries present on disk (markdown)|14|
|Registries with status columns|9|
|Registries with status-bearing rows|2|
|Status-bearing rows|29|
|Done rows|12 (41.4%)|
|Blocked rows|0|
|Rewrite artifacts (total / done / outstanding)|23 / 12 / 11|
|Open questions (total / done / outstanding)|0 / 0 / 0|
|Open questions blocking=yes (outstanding)|0|
|Draft-2 sources with mapping rows|0 / 5|

#### Summary

- Status-bearing rows: 29
- Done (DN): 12 (41.4%)

|Status|Count|
|---|---:|
|NS|17|
|DN|12|

#### Per-registry status distribution

|Registry|Total|NS|IP|RV|DN|BL|
|---|---:|---:|---:|---:|---:|---:|
|`change_control.md`|0|0|0|0|0|0|
|`cli_parity_deltas.md`|0|0|0|0|0|0|
|`master_mapping_ledger.md`|6|6|0|0|0|0|
|`open_questions.md`|0|0|0|0|0|0|
|`plan_overlay_register.md`|0|0|0|0|0|0|
|`rewrite_status.md`|23|11|0|0|12|0|
|`roadmap_register.md`|0|0|0|0|0|0|
|`supersedence_ledger.md`|0|0|0|0|0|0|
|`terminology_map.md`|0|0|0|0|0|0|

#### Top blocked rows

*No blocked rows found.*

#### Open questions: distribution

*No rows found.*

#### Open questions: outstanding

*No outstanding items.*

#### Rewrite status: distribution

|Status|Count|
|---|---:|
|DN|12|
|NS|11|

#### Rewrite status: outstanding

|Artifact|Status|Owner|Next action|
|---|---|---|---|
|ADR-0001 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|ADR-0002 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|ADR-0003 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|ADR-0004 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|ADR-0005 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|ADR-0006 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|ADR-0007 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|ADR-0008 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|ADR-0009 (active rewrite)|NS||Draft-2 extraction + mapping gate|
|Reference specs (folder)|NS||Create minimum set per plan|
|CLI contract docs (folder)|NS||Create contract + inventories per plan|

#### Rewrite status: next actions

|Artifact|Status|Next action|
|---|---|---|
|ADR-0001 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|ADR-0002 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|ADR-0003 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|ADR-0004 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|ADR-0005 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|ADR-0006 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|ADR-0007 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|ADR-0008 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|ADR-0009 (active rewrite)|NS|Draft-2 extraction + mapping gate|
|Reference specs (folder)|NS|Create minimum set per plan|
|CLI contract docs (folder)|NS|Create contract + inventories per plan|

#### Rewrite status: staleness (dated outstanding)

*No dated outstanding items found.*

#### Draft-2 sources: status distribution

|Status|Count|
|---|---:|
|NS|5|

#### Draft-2 mapping rows: status distribution

*No effective mapping rows found.*

#### Draft-2 sources: inventory

|Source ID|File|Status|Mapping rows|
|---|---|---|---:|
|D2-0001|`ADR-0001 Include and Exclude-draft-2.md`|NS|0|
|D2-0002|`ADR-0002 Plugin Engines-draft-2.md`|NS|0|
|D2-0003|`ADR-0003 Policy Boundaries-draft-2.md`|NS|0|
|D2-0004|`ADR-0004 Taxonomy-draft-2.md`|NS|0|
|D2-0005|`ADR-0005 Naming Conventions-draft-2.md`|NS|0|

#### Draft-2 mapping coverage

- Effective mapping rows: 0
- Draft-2 sources: 5
- Draft-2 sources with mapping rows: 0

#### Registry coverage

*No unindexed registry markdown files found.*
<!-- GENERATED:END s11r2-progress -->
