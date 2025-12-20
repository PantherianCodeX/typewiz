# CLI help snapshot

Captured: 2025-12-19

Invocation:

```bash
PYTHONPATH=src python -m ratchetr --help
```

Output:

```text
usage: ratchetr [-h] [--out {text,json}] [--config CONFIG] [--root ROOT]
                [--ratchetr-dir RATCHETR_DIR] [--manifest MANIFEST]
                [--cache-dir CACHE_DIR] [--log-dir LOG_DIR]
                [--log-format {text,json}]
                [--log-level {debug,info,warning,error}] [--version]
                {audit,manifest,query,ratchet,help,cache,engines,dashboard,init,readiness}
                ...

Collect typing diagnostics and readiness insights for Python projects. `rtr`
is an alias.

positional arguments:
  {audit,manifest,query,ratchet,help,cache,engines,dashboard,init,readiness}
    audit               Run typing audits and produce manifests/dashboards
    manifest            Work with manifest files (validate)
    query               Inspect sections of a manifest summary without
                        external tools
    ratchet             Manage per-file ratchet budgets
    help                Show CLI topic documentation
    cache               Inspect or clear ratchetr caches
    engines             Inspect discovered ratchetr engines
    dashboard           Render a summary from an existing manifest
    init                Generate a starter configuration file
    readiness           Show top-N candidates for strict typing

options:
  -h, --help            show this help message and exit
  --out {text,json}     Stdout format for structured output (text|json).
                        (default: text)
  --config CONFIG       Optional ratchetr.toml path (default: search from
                        cwd). (default: None)
  --root ROOT           Repository root override. (default: None)
  --ratchetr-dir RATCHETR_DIR
                        Tool home directory override (default:
                        <root>/.ratchetr). (default: None)
  --manifest MANIFEST   Manifest path override. (default: None)
  --cache-dir CACHE_DIR
                        Cache directory override. (default: None)
  --log-dir LOG_DIR     Log directory override. (default: None)
  --log-format {text,json}
                        Select logging output format (human-readable text or
                        structured JSON). (default: text)
  --log-level {debug,info,warning,error}
                        Set verbosity of logged events. (default: info)
  --version             Print the ratchetr version and exit. (default: False)
```
