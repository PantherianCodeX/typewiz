# CLI help snapshot

Captured: 2025-12-19

Invocation:

```bash
PYTHONPATH=src python -m ratchetr ratchet --help
```

Output:

```text
usage: ratchetr ratchet [-h] [--out {text,json}] [--config CONFIG]
                        [--root ROOT] [--ratchetr-dir RATCHETR_DIR]
                        [--manifest MANIFEST] [--cache-dir CACHE_DIR]
                        [--log-dir LOG_DIR] [--log-format {text,json}]
                        [--log-level {debug,info,warning,error}]
                        {init,check,update,rebaseline-signature,info} ...

positional arguments:
  {init,check,update,rebaseline-signature,info}
    init                Create a ratchet budget from a manifest
    check               Compare a manifest against a ratchet budget
    update              Update ratchet budgets using a manifest
    rebaseline-signature
                        Refresh engine signature data without changing budgets
    info                Show resolved ratchet configuration

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
