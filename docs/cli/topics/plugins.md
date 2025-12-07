# Engines

> Alpha-quality 0.1.x — the engine registry and CLI flags are stable for mypy and pyright, but third-party engine APIs may evolve in 0.1.x.

Typewiz runs typing engines (pyright, mypy, and custom engines) under a unified
interface. Configure engines in `typewiz.toml`:

- `[audit.runners]` controls which engines run by default.
- `[audit.engines.NAME]` defines engine arguments, include/exclude filters, and
  default profiles.
- `[audit.engines.NAME.profiles.PROFILE]` refines settings per profile.

Override profiles or engine arguments at runtime with `typewiz audit --profile ENGINE PROFILE`
and `--plugin-arg ENGINE=ARG`. Engine names match those reported by `typewiz engines` and stored
in the manifest.

Third-party engines are discovered via the `typewiz.engines` entry point group and must implement
the `typewiz.engines.BaseEngine` protocol. See `src/typewiz/engines/base.py` and the example
engine in `examples/plugins/simple_engine.py` for a minimal implementation.

Use `typewiz help overview` and `docs/typewiz.md` for a deeper architecture overview, and
`examples/typewiz.sample.toml` for a configuration template showing multiple engines.
