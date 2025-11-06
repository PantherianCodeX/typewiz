# Typewiz CLI Overview

The `typewiz` command orchestrates typing audits, manifest tooling, and ratchet budgeting.
Common entry points:

- `typewiz audit`: run configured engines and produce manifests/dashboards.
- `typewiz query`: inspect existing manifests in structured formats.
- `typewiz ratchet`: manage per-file budgets derived from manifests.
- `typewiz manifest`: validate manifests or emit the JSON schema.
- `typewiz help <topic>`: view contextual documentation like this page.

Run `typewiz --help` to see every command and flag. Combine subcommand `--help`
for detailed usage, e.g. `typewiz audit --help`.
