# CLI help snapshot

Captured: 2025-12-19

Invocation:

```bash
PYTHONPATH=src python -m ratchetr audit --help
```

Output:

```text
usage: ratchetr audit [-h] [--out {text,json}] [--config CONFIG] [--root ROOT]
                      [--ratchetr-dir RATCHETR_DIR] [--manifest MANIFEST]
                      [--cache-dir CACHE_DIR] [--log-dir LOG_DIR]
                      [--log-format {text,json}]
                      [--log-level {debug,info,warning,error}]
                      [--runner RUNNERS] [--mode MODES]
                      [--max-depth MAX_DEPTH] [--max-files MAX_FILES]
                      [--max-fingerprint-bytes MAX_FINGERPRINT_BYTES]
                      [--hash-workers WORKERS] [--respect-gitignore]
                      [--plugin-arg RUNNER=ARG] [--profile RUNNER PROFILE]
                      [-S {compact,expanded,full}]
                      [--summary-fields SUMMARY_FIELDS]
                      [--fail-on {never,none,warnings,errors,any}]
                      [-s FORMAT[:PATH]] [-d FORMAT[:PATH]]
                      [--compare-to COMPARE_TO] [--dry-run]
                      [--dashboard-view {overview,engines,hotspots,readiness,runs}]
                      [--readiness [TOKEN ...]]
                      [PATH ...]

Collect diagnostics from configured engines and optionally write manifests or
dashboards.

positional arguments:
  PATH                  Directories to include in audit scope (default: auto-
                        detected python packages). Specify at end of command.
                        (default: None)

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
  --runner RUNNERS      Limit to specific engines (repeatable). (default:
                        None)
  --mode MODES          Select which modes to run (repeatable: current,
                        target). (default: None)
  --max-depth MAX_DEPTH
                        Limit directory recursion depth for fingerprinting.
                        (default: None)
  --max-files MAX_FILES
                        Limit number of files fingerprinted per run. (default:
                        None)
  --max-fingerprint-bytes MAX_FINGERPRINT_BYTES
                        Limit bytes fingerprinted per file. (default: None)
  --hash-workers WORKERS
                        Hash worker pool size ('auto' or non-negative
                        integer). (default: None)
  --respect-gitignore   Respect .gitignore rules when expanding directories.
                        (default: False)
  --plugin-arg RUNNER=ARG
                        Pass an extra argument to a runner (repeatable).
                        Example: --plugin-arg pyright=--verifytypes (default:
                        [])
  --profile RUNNER PROFILE
                        Activate a named profile for a runner (repeatable).
                        (default: [])
  -S {compact,expanded,full}, --summary {compact,expanded,full}
                        Compact (default), expanded (multi-line), or full
                        (expanded + all fields). (default: compact)
  --summary-fields SUMMARY_FIELDS
                        Comma-separated extra summary fields (profile, config,
                        plugin-args, paths, all). Ignored for --summary=full.
                        (default: None)
  --fail-on {never,none,warnings,errors,any}
                        Non-zero exit when diagnostics reach this severity
                        (aliases: none=never, any=any finding). (default:
                        None)
  -s FORMAT[:PATH], --save-as FORMAT[:PATH]
                        Save output in one or more formats (repeatable, each
                        takes exactly one FORMAT[:PATH] value). (default:
                        None)
  -d FORMAT[:PATH], --dashboard FORMAT[:PATH]
                        Save output in one or more formats (repeatable, each
                        takes exactly one FORMAT[:PATH] value). (default:
                        None)
  --compare-to COMPARE_TO
                        Optional path to a previous manifest to compare totals
                        against (adds deltas to CI line). (default: None)
  --dry-run             Skip writing manifests and dashboards; report
                        summaries only. (default: False)
  --dashboard-view {overview,engines,hotspots,readiness,runs}
                        Default tab when writing the HTML dashboard. (default:
                        overview)
  --readiness [TOKEN ...]
                        Use key=value tokens (level=, status=, limit=,
                        severity=) and boolean toggles (details/no-details).
                        (default: None)
```
