# Engines

> Alpha-quality 0.1.x — the engine registry and CLI flags are stable for mypy and pyright, but third-party engine APIs may evolve in 0.1.x.

ratchetr runs typing engines (pyright, mypy, and custom engines) under a unified
interface. Configure engines in `ratchetr.toml`:

- `[audit.runners]` controls which engines run by default.
- `[audit.engines.NAME]` defines engine arguments, include/exclude filters, and
  default profiles.
- `[audit.engines.NAME.profiles.PROFILE]` refines settings per profile.

Override profiles or engine arguments at runtime with `ratchetr audit --profile ENGINE PROFILE`
and `--plugin-arg ENGINE=ARG`. Engine names match those reported by `ratchetr engines` and stored
in the manifest.

Third-party engines are discovered via the `ratchetr.engines` entry point group and must implement
the `ratchetr.engines.BaseEngine` protocol. See `src/ratchetr/engines/base.py` and the example
engine in `examples/plugins/simple_engine.py` for a minimal implementation.

Use `ratchetr help overview` and `docs/ratchetr.md` for a deeper architecture overview, and
`examples/ratchetr.sample.toml` for a configuration template showing multiple engines.
