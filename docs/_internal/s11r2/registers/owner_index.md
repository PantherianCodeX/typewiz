# Owner index (one concept, one owner)

This is the enforcement register for concept ownership. It should remain consistent with the plan’s canonical ownership matrix.

## Rules

- Each *normative* concept appears once here.
- The “Canonical owner” is the only doc allowed to define the concept in full.
- Non-owners may include brief summaries but must link to the canonical owner.

## Canonical ownership (seed from ADR Rewrite Plan v18 §2.2)

| Concept | Canonical owner | Non-owner allowed content (max) | Links required |
| --- | --- | --- | --- |
| Workspace vs modes; Project vs Ad-hoc | ADR-0003 | brief context only | link to ADR-0003 |
| Source precedence; `--no-env`; disclosure of disabled sources | ADR-0003 | brief context only | link to ADR-0003 |
| CLI boundary argv normalization (macro expansion; macro-only dedup/warnings) | ADR-0003 (impl note in `docs/_internal/cli/argv_normalization.md`) | pointers only | link to owner + impl note |
| Mandatory run summary contract (minimum fields) | ADR-0003 (details in `docs/reference/run_summary.md`) | pointers only | link to ADR + reference |
| Findings schema ownership and sources | ADR-0003 (details in `docs/reference/findings.md`) | pointers only | link to ADR + reference |
| Formal run artifact set (run summary, findings, resolution log) | ADR-0003 + `docs/reference/run_artifacts.md` | pointers only | link to ADR + reference |
| Stable identifiers and token/hash rules (`finding_id`, path tokens, `link_chain_id`) | `docs/reference/identifiers.md` | pointers only | link to reference |
| Stable code registry (findings, warnings, engine failures) | `docs/reference/error_codes.md` | pointers only | link to reference |
| Base/project-root semantics; `^`; canonical rendering; absolute gating | ADR-0006 (details in `docs/reference/path_resolution.md`) | pointers only | link to ADR + reference |
| Selector semantics (targets/include/exclude; ordering; rejection policy; absolute gating) | `docs/reference/selector_semantics.md` (decision recorded in ADR-0001) | pointers only | link to reference + ADR-0001 |
| Follow modes; boundary inclusion; link-chain provenance schema | ADR-0008 (details in `docs/reference/follow_link.md`) | pointers only | link to ADR + reference |
| Artifacts/writes policy; cache; logs | ADR-0007 (details in `docs/reference/artifacts.md` / `cache.md`) | pointers only | link to ADR + references |
| Tool home + destination taxonomy + defaults locations | ADR-0007 (defaults in `docs/reference/defaults.md`) | pointers only | link to ADR + references |
| Config discovery/loading; `pyproject.toml` parity | ADR-0009 (details in `docs/reference/config_loading.md` and `docs/reference/env_vars.md`) | pointers only | link to ADR + references |
| Engine plan dedupe/equivalence; failure aggregation | ADR-0002 | pointers only | link to ADR-0002 |
| Repository layering taxonomy | ADR-0004 | brief context only | link to ADR-0004 |
| Naming rules and boundary translation | ADR-0005 | brief context only | link to ADR-0005 |

## Additions

Add new rows only if the plan introduces new owned concepts or new reference specs become canonical owners.
