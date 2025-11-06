# Plugins & Engines

Typewiz runs typing engines (Pyright, mypy, custom plugins) under a unified
interface. Configure engines in `typewiz.toml`:

- `[audit.runners]` controls default engines.
- `[audit.engines.NAME]` defines plugin arguments, include/exclude filters, and
  default profiles.
- `[audit.engines.NAME.profiles.PROFILE]` refines settings per profile.

Override profiles or plugin arguments at runtime with `typewiz audit --profile NAME PROFILE`
and `--plugin-arg NAME=ARG`. For advanced integrations, ship adapters conforming to the
plugin registry (see `typewiz.plugins` package) then list them in configuration.

Use `typewiz help overview` to revisit core CLI behaviour.
