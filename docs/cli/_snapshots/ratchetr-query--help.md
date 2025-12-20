# CLI help snapshot

Captured: 2025-12-19

Invocation:

```bash
PYTHONPATH=src python -m ratchetr query --help
```

Output:

```text
usage: ratchetr query [-h] [--out {text,json}] [--config CONFIG] [--root ROOT]
                      [--ratchetr-dir RATCHETR_DIR] [--manifest MANIFEST]
                      [--cache-dir CACHE_DIR] [--log-dir LOG_DIR]
                      [--log-format {text,json}]
                      [--log-level {debug,info,warning,error}]
                      {overview,hotspots,readiness,runs,engines,rules} ...

positional arguments:
  {overview,hotspots,readiness,runs,engines,rules}
    overview            Show severity totals, with optional category and run
                        breakdowns
    hotspots            List top offending files or folders
    readiness           Show readiness candidates for strict typing
    runs                Inspect individual typing runs
    engines             Display engine configuration used for runs
    rules               Show the most common rule diagnostics

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
```
