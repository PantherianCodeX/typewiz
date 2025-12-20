# s11r2 progress board

## Generated

Timestamp: 2025-12-20T09:11:36+00:00

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
|Registries with status-bearing rows|4|
|Status-bearing rows|52|
|Done rows|17 (32.7%)|
|Blocked rows|0|
|Rewrite artifacts (total / done / outstanding)|23 / 12 / 11|
|Open questions (total / done / outstanding)|0 / 0 / 0|
|Open questions blocking=yes (outstanding)|0|
|Draft-2 sources with mapping rows|2 / 5|

#### Summary

- Status-bearing rows: 52
- Done (DN): 17 (32.7%)

|Status|Count|
|---|---:|
|RV|19|
|DN|17|
|IP|8|
|NS|8|

#### Per-registry status distribution

|Registry|Total|NS|IP|RV|DN|BL|
|---|---:|---:|---:|---:|---:|---:|
|`change_control.md`|5|0|0|0|5|0|
|`cli_parity_deltas.md`|0|0|0|0|0|0|
|`master_mapping_ledger.md`|20|8|0|12|0|0|
|`open_questions.md`|0|0|0|0|0|0|
|`plan_overlay_register.md`|4|0|0|4|0|0|
|`rewrite_status.md`|23|0|8|3|12|0|
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
|IP|8|
|RV|3|

#### Rewrite status: outstanding

|Artifact|Status|Owner|Next action|
|---|---|---|---|
|ADR-0001 (active rewrite)|IP||Draft-2 extraction + mapping gate|
|ADR-0002 (active rewrite)|IP||Draft-2 extraction + mapping gate|
|ADR-0003 (active rewrite)|RV||Review Phase 2 rewrite + mapping evidence|
|ADR-0004 (active rewrite)|IP||Draft-2 extraction + mapping gate|
|ADR-0005 (active rewrite)|IP||Draft-2 extraction + mapping gate|
|ADR-0006 (active rewrite)|RV||Review Phase 2 rewrite + mapping evidence|
|ADR-0007 (active rewrite)|IP||Draft-2 extraction + mapping gate|
|ADR-0008 (active rewrite)|IP||Draft-2 extraction + mapping gate|
|ADR-0009 (active rewrite)|IP||Draft-2 extraction + mapping gate|
|Reference specs (folder)|RV||Review Phase 2 reference specs for run summary/findings/errors/artifacts/identifiers/path resolution|
|CLI contract docs (folder)|IP||Populate Phase 3-6 content|

#### Rewrite status: next actions

|Artifact|Status|Next action|
|---|---|---|
|ADR-0001 (active rewrite)|IP|Draft-2 extraction + mapping gate|
|ADR-0002 (active rewrite)|IP|Draft-2 extraction + mapping gate|
|ADR-0003 (active rewrite)|RV|Review Phase 2 rewrite + mapping evidence|
|ADR-0004 (active rewrite)|IP|Draft-2 extraction + mapping gate|
|ADR-0005 (active rewrite)|IP|Draft-2 extraction + mapping gate|
|ADR-0006 (active rewrite)|RV|Review Phase 2 rewrite + mapping evidence|
|ADR-0007 (active rewrite)|IP|Draft-2 extraction + mapping gate|
|ADR-0008 (active rewrite)|IP|Draft-2 extraction + mapping gate|
|ADR-0009 (active rewrite)|IP|Draft-2 extraction + mapping gate|
|Reference specs (folder)|RV|Review Phase 2 reference specs for run summary/findings/errors/artifacts/identifiers/path resolution|
|CLI contract docs (folder)|IP|Populate Phase 3-6 content|

#### Rewrite status: staleness (dated outstanding)

|Artifact|Status|Last touch|Age (days)|Next action|
|---|---|---|---:|---|
|ADR-0001 (active rewrite)|IP|2025-12-19|1|Draft-2 extraction + mapping gate|
|ADR-0002 (active rewrite)|IP|2025-12-19|1|Draft-2 extraction + mapping gate|
|ADR-0004 (active rewrite)|IP|2025-12-19|1|Draft-2 extraction + mapping gate|
|ADR-0005 (active rewrite)|IP|2025-12-19|1|Draft-2 extraction + mapping gate|
|ADR-0007 (active rewrite)|IP|2025-12-19|1|Draft-2 extraction + mapping gate|
|ADR-0008 (active rewrite)|IP|2025-12-19|1|Draft-2 extraction + mapping gate|
|ADR-0009 (active rewrite)|IP|2025-12-19|1|Draft-2 extraction + mapping gate|
|CLI contract docs (folder)|IP|2025-12-19|1|Populate Phase 3-6 content|
|ADR-0003 (active rewrite)|RV|2025-12-20|0|Review Phase 2 rewrite + mapping evidence|
|ADR-0006 (active rewrite)|RV|2025-12-20|0|Review Phase 2 rewrite + mapping evidence|
|Reference specs (folder)|RV|2025-12-20|0|Review Phase 2 reference specs for run summary/findings/errors/artifacts/identifiers/path resolution|

#### Sources: status distribution

|Status|Count|
|---|---:|
|NS|8|
|RV|3|

#### Mapping rows: status distribution

|Status|Count|
|---|---:|
|RV|9|

#### Sources: inventory

|Source ID|File|Status|Mapping rows|
|---|---|---|---:|
|D2-0001|`ADR-0001 Include and Exclude-draft-2.md`|RV|2|
|D2-0002|`ADR-0002 Plugin Engines-draft-2.md`|NS|0|
|D2-0003|`ADR-0003 Policy Boundaries-draft-2.md`|RV|7|
|D2-0004|`ADR-0004 Taxonomy-draft-2.md`|NS|0|
|D2-0005|`ADR-0005 Naming Conventions-draft-2.md`|NS|0|
|PLAN-v19|`ADR Rewrite Plan v19.md`|RV|0|
|SUP-0001|`0001/path_scoping_contract.md`|NS|0|
|SUP-0002|`0001/reference_implementation_outline.md`|NS|0|
|SUP-0003|`0001/test_matrix.md`|NS|0|
|SUP-0004|`0002/execution outline.md`|NS|0|
|SUP-0005|`0002/test matrix.md`|NS|0|

#### Sources with zero mapping rows

- D2-0002
- D2-0004
- D2-0005
- PLAN-v19
- SUP-0001
- SUP-0002
- SUP-0003
- SUP-0004
- SUP-0005

#### Registry coverage

*No unindexed registry markdown files found.*
<!-- GENERATED:END s11r2-progress -->
