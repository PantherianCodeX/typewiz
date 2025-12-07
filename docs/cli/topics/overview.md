# Typewiz CLI Overview

> Alpha-quality 0.1.x — APIs, CLI flags, and dashboards may change without deprecation, but schemas and error codes are converging.

The `typewiz` command orchestrates typing audits, manifest tooling, ratchet budgets, and dashboards.
Common entry points:

- `typewiz audit`: run configured engines and produce manifests/dashboards.
- `typewiz query`: inspect existing manifests in structured formats.
- `typewiz ratchet`: manage per-file ratchet budgets derived from manifests.
- `typewiz manifest`: validate manifests or emit the JSON schema.
- `typewiz engines`: list discovered engines (built-ins + entry points).
- `typewiz cache`: clear `.typewiz_cache/` when fingerprints need to be rebuilt.
- `typewiz help <topic>`: view contextual documentation like this page.

Run `typewiz --help` to see every command and flag. Combine subcommand `--help`
for detailed usage, e.g. `typewiz audit --help`.

For a deeper architecture overview, see `docs/typewiz.md`. Configuration-heavy
examples live under `examples/` and `examples/typewiz.sample.toml`.

Related CLI topics:

- `typewiz help manifest` / `docs/cli/topics/manifest.md`
- `typewiz help ratchet` / `docs/cli/topics/ratchet.md`
- `typewiz help query` / `docs/cli/topics/query.md`
- `typewiz help engines` / `docs/cli/topics/plugins.md`
