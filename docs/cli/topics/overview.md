# ratchetr CLI Overview

> Alpha-quality 0.1.x — APIs, CLI flags, and dashboards may change without deprecation, but schemas and error codes are converging.

The `ratchetr` command orchestrates typing audits, manifest tooling, ratchet budgets, and dashboards.
Common entry points:

- `ratchetr audit`: run configured engines and produce manifests/dashboards.
- `ratchetr query`: inspect existing manifests in structured formats.
- `ratchetr ratchet`: manage per-file ratchet budgets derived from manifests.
- `ratchetr manifest`: validate manifests or emit the JSON schema.
- `ratchetr engines`: list discovered engines (built-ins + entry points).
- `ratchetr cache`: clear `.ratchetr_cache/` when fingerprints need to be rebuilt.
- `ratchetr help <topic>`: view contextual documentation like this page.

Run `ratchetr --help` to see every command and flag. Combine subcommand `--help`
for detailed usage, e.g. `ratchetr audit --help`.

For a deeper architecture overview, see `docs/ratchetr.md`. Configuration-heavy
examples live under `examples/` and `examples/ratchetr.sample.toml`.

Related CLI topics:

- `ratchetr help manifest` / `docs/cli/topics/manifest.md`
- `ratchetr help ratchet` / `docs/cli/topics/ratchet.md`
- `ratchetr help query` / `docs/cli/topics/query.md`
- `ratchetr help engines` / `docs/cli/topics/plugins.md`

## Draft log

### 2025-12-19 — Phase 1 stub scaffold

- **Change:** Created Phase 1 stub with required header block and section scaffolding.
- **Preservation:** N/A (Phase 1 stub; no draft-2 items mapped).
- **Overlay:** N/A (no Plan v19 deltas applied).
- **Mapping:** N/A (no MAP/P/CF entries yet).
- **Supersedence:** N/A.
- **Notes / risks:** None.
