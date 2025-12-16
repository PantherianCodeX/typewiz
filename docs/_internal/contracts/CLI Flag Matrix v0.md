# ratchetr CLI Flag Reference

> Comprehensive flag inventory for all ratchetr commands

This document provides a complete reference for all CLI flags, their precedence, valid values, and error behaviors.

## Global Flags

Available across all commands:

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--out` | | choice | `text` | CLI only | `text`, `json` | "invalid choice" |
| `--config` | | option | auto-discovery | CLI > `RATCHETR_CONFIG` > discovery | valid file path | "config file not found" or parse error |
| `--root` | | option | auto-discovery | CLI > `RATCHETR_ROOT` > discovery | valid directory | directory validation error |
| `--ratchetr-dir` | | option | `<root>/.ratchetr` | CLI > `RATCHETR_DIR` > config > default | valid directory | creates if missing |
| `--manifest` | | option | `<tool_home>/manifest.json` | CLI > `RATCHETR_MANIFEST` > config > default | valid file path | context-dependent (discovery or error) |
| `--cache-dir` | | option | `<tool_home>/.cache` | CLI > `RATCHETR_CACHE_DIR` > config > default | valid directory | creates if missing |
| `--log-dir` | | option | `<tool_home>/logs` | CLI > `RATCHETR_LOG_DIR` > config > default | valid directory | creates if missing |
| `--log-format` | | choice | `text` | CLI only | `text`, `json` | "invalid choice" |
| `--log-level` | | choice | `info` | CLI only | `debug`, `info`, `warning`, `error` | "invalid choice" |
| `--version` | | flag | `false` | CLI only | n/a | n/a |
| `--help` | `-h` | flag | `false` | CLI only | n/a | n/a |

---

## Command: audit

Run typing audits and produce manifests/dashboards.

### Positional Arguments

| Argument | Type | Default | Precedence | Description | Error Behavior |
|----------|------|---------|------------|-------------|----------------|
| `PATH` | list | `["."]` (CURRENT mode) or env/config (TARGET mode) | CLI > `RATCHETR_INCLUDE` > config > default | Directories/files to audit | "path not found" if invalid |

### Options

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--runner` | | repeatable | all enabled | CLI > config | valid engine names | runs all if not specified |
| `--mode` | | repeatable | `BOTH` | CLI only | `current`, `target` | "invalid choice" |
| `--max-depth` | | option | unlimited | CLI only | non-negative integer | type error |
| `--max-files` | | option | unlimited | CLI only | non-negative integer | type error |
| `--max-fingerprint-bytes` | | option | unlimited | CLI only | non-negative integer | type error |
| `--hash-workers` | | option | auto | CLI only | `auto` or non-negative integer | parse error |
| `--respect-gitignore` | | flag | `false` | CLI only | n/a | n/a |
| `--plugin-arg` | | repeatable | `[]` | CLI only | `RUNNER=ARG` format | parse error if malformed |
| `--profile` | | repeatable | `[]` | CLI only | `RUNNER PROFILE` pairs | requires both values |
| `--summary` | `-S` | choice | `compact` | CLI only | `compact`, `expanded`, `full` | "invalid choice" |
| `--summary-fields` | | option | none | CLI only | comma-separated field names | invalid field warning |
| `--fail-on` | | choice | config or `never` | CLI > config > default | `never`, `none`, `warnings`, `errors`, `any` | "invalid choice" |
| `--save-as` | `-s` | repeatable | none | CLI only | `FORMAT[:PATH]` (json only) | "invalid format" or path errors |
| `--dashboard` | `-d` | repeatable | config or none | CLI > config > none | `FORMAT[:PATH]` (json/markdown/html) | "invalid format" or path errors |
| `--compare-to` | | option | none | CLI only | valid manifest path | file not found or parse error |
| `--dry-run` | | flag | `false` | CLI only | n/a | n/a |
| `--dashboard-view` | | choice | `overview` | CLI only | `overview`, `engines`, `hotspots`, `readiness`, `runs` | "invalid choice" |
| `--readiness` | | special | none | CLI only | `TOKEN ...` (key=value pairs) | parse error if malformed |

### Precedence Notes

**Scope Paths** (CURRENT vs TARGET modes):

- **CURRENT mode**: CLI positional args participate (`rtr audit src` → CURRENT scans `src/`, TARGET scans from env/config/default)
- **TARGET mode**: CLI positional args DO NOT participate (both CURRENT and TARGET use env/config/default)
- Precedence chain: CLI positional (CURRENT only) > `RATCHETR_INCLUDE` > config `audit.default_include` > default `["."]`

---

## Command: dashboard

Render a summary from an existing manifest.

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--save-as` | `-s` | repeatable | `html:<tool_home>/dashboard.html` | CLI only | `FORMAT[:PATH]` (json/markdown/html) | "invalid format" or path errors |
| `--view` | | choice | `overview` | CLI only | `overview`, `engines`, `hotspots`, `readiness`, `runs` | "invalid choice" |
| `--dry-run` | | flag | `false` | CLI only | n/a | n/a |

---

## Command: init

Generate a starter configuration file.

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--save-as` | `-s` | option | `ratchetr.toml` | CLI only | valid file path | path creation errors |
| `--force` | | flag | `false` | CLI only | n/a | refuses to overwrite without force |

---

## Command: readiness

Show top-N candidates for strict typing.

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--readiness` | | special | enabled by default | CLI only | `TOKEN ...` (key=value pairs) | parse error if malformed |

---

## Command: manifest

Work with manifest files.

### Subcommand: validate

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `PATH` | (positional) | option | discovery | CLI > discovery | valid manifest path | "manifest not found" |
| `--schema` | | option | built-in | CLI only | valid JSON schema path | "schema not found" or parse error |

### Subcommand: schema

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--save-as` | `-s` | option | stdout | CLI only | valid file path | path creation errors |
| `--indent` | | option | `2` | CLI only | non-negative integer | type error |

---

## Command: query

Inspect sections of a manifest summary.

### Global Query Options

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--save-as` | `-s` | repeatable | stdout | CLI only | `FORMAT[:PATH]` (json only) | "invalid format" or path errors |

### Subcommand: overview

| Flag | Type | Default | Description | Error Behavior |
|------|------|---------|-------------|----------------|
| `--include-categories` | flag | `false` | Include category totals | n/a |
| `--include-runs` | flag | `false` | Include per-run severity totals | n/a |

### Subcommand: hotspots

| Flag | Type | Default | Valid Values | Error Behavior |
|------|------|---------|--------------|----------------|
| `--kind` | choice | `files` | `files`, `folders` | "invalid choice" |
| `--limit` | option | `10` | non-negative integer | type error |

### Subcommand: readiness

| Flag | Type | Default | Description | Error Behavior |
|------|------|---------|-------------|----------------|
| `--readiness` | special | enabled | `TOKEN ...` (key=value pairs) | parse error if malformed |

### Subcommand: runs

| Flag | Type | Default | Description | Error Behavior |
|------|------|---------|-------------|----------------|
| `--tool` | repeatable | all | Filter by engine name | none (filters results) |
| `--mode` | repeatable | all | Filter by mode | none (filters results) |
| `--limit` | option | `10` | Maximum runs to return | type error |

### Subcommand: engines

| Flag | Type | Default | Description | Error Behavior |
|------|------|---------|-------------|----------------|
| `--limit` | option | `10` | Maximum rows to return | type error |

### Subcommand: rules

| Flag | Type | Default | Description | Error Behavior |
|------|------|---------|-------------|----------------|
| `--limit` | option | `10` | Maximum rules to return | type error |
| `--include` | flag | `false` | Include top file paths per rule | n/a |

---

## Command: ratchet

Manage per-file ratchet budgets.

### Subcommand: init

Create a ratchet budget from a manifest.

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--save-as` | `-s` | option | `<root>/ratchet.json` | CLI > config > default | valid file path | path errors |
| `--run` | | repeatable | all | CLI > config | `tool:mode` format | parse error if malformed |
| `--severities` | | option | `errors,warnings` | CLI > config > default | comma-separated severities | invalid severity error |
| `--target` | | repeatable | none | CLI only | `SEVERITY=COUNT` format | parse error if malformed |
| `--force` | | flag | `false` | CLI only | n/a | refuses to overwrite without force |

### Subcommand: check

Compare a manifest against a ratchet budget.

| Flag | Type | Default | Precedence | Valid Values | Error Behavior |
|------|------|---------|------------|--------------|----------------|
| `--ratchet` | option | discovery | CLI > config > discovery | valid ratchet path | "ratchet not found" |
| `--run` | repeatable | all | CLI > config | `tool:mode` format | parse error if malformed |
| `--signature-policy` | choice | config or `fail` | CLI > config > default | `fail`, `warn`, `ignore` | "invalid choice" |
| `--limit` | option | unlimited | CLI > config | non-negative integer | type error |
| `--summary-only` | flag | `false` | CLI > config | n/a | n/a |

### Subcommand: update

Update ratchet budgets using a manifest.

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--ratchet` | | option | discovery | CLI > config > discovery | valid ratchet path | "ratchet not found" |
| `--save-as` | `-s` | option | `--ratchet` value | CLI only | valid file path | path errors |
| `--run` | | repeatable | all | CLI > config | `tool:mode` format | parse error if malformed |
| `--target` | | repeatable | none | CLI only | `SEVERITY=COUNT` format | parse error if malformed |
| `--dry-run` | | flag | `false` | CLI only | n/a | n/a |
| `--force` | | flag | `false` | CLI only | n/a | requires force to overwrite |
| `--limit` | | option | unlimited | CLI > config | non-negative integer | type error |
| `--summary-only` | | flag | `false` | CLI > config | n/a | n/a |

### Subcommand: rebaseline-signature

Refresh engine signature data without changing budgets.

| Flag | Alias | Type | Default | Precedence | Valid Values | Error Behavior |
|------|-------|------|---------|------------|--------------|----------------|
| `--ratchet` | | option | discovery | CLI > config > discovery | valid ratchet path | "ratchet not found" |
| `--save-as` | `-s` | option | `--ratchet` value | CLI only | valid file path | path errors |
| `--run` | | repeatable | all | CLI > config | `tool:mode` format | parse error if malformed |
| `--force` | | flag | `false` | CLI only | n/a | requires force to overwrite |

### Subcommand: info

Show resolved ratchet configuration.

| Flag | Type | Default | Precedence | Valid Values | Error Behavior |
|------|------|---------|------------|--------------|----------------|
| `--ratchet` | option | discovery | CLI > config > discovery | valid ratchet path | displays computed if not found |
| `--run` | repeatable | all | CLI > config | `tool:mode` format | parse error if malformed |

---

## Environment Variables

All path-related environment variables:

| Variable | Applies To | Type | Purpose | Default |
|----------|-----------|------|---------|---------|
| `RATCHETR_ROOT` | all commands | path | Override repository root | auto-discovery |
| `RATCHETR_CONFIG` | all commands | path | Override config file location | auto-discovery |
| `RATCHETR_DIR` | all commands | path | Override tool home directory | `<root>/.ratchetr` |
| `RATCHETR_MANIFEST` | all commands | path | Override manifest location | `<tool_home>/manifest.json` |
| `RATCHETR_CACHE_DIR` | all commands | path | Override cache directory | `<tool_home>/.cache` |
| `RATCHETR_LOG_DIR` | all commands | path | Override log directory | `<tool_home>/logs` |
| `RATCHETR_INCLUDE` | audit only | JSON array | Override include paths for audit scope | config or `["."]` |

---

## Path Resolution Semantics

### Trailing Slash Convention

For output flags (`--save-as`, `--dashboard`):

1. **Omitted** → default filename at default location

   ```bash
   rtr audit --save-as json
   # → .ratchetr/manifest.json
   ```

2. **`directory/`** (trailing `/`) → default filename in specified directory

   ```bash
   rtr audit --dashboard html:reports/
   # → reports/dashboard.html
   ```

3. **`filename.ext`** (no trailing `/`) → specified filename

   ```bash
   rtr audit --save-as json:custom.json
   # → custom.json
   ```

4. **`/abs/path/`** (absolute + trailing `/`) → default filename in absolute directory

   ```bash
   rtr audit --dashboard html:/tmp/
   # → /tmp/dashboard.html
   ```

5. **`/abs/path/file.ext`** → absolute file path

   ```bash
   rtr audit --save-as json:/tmp/audit.json
   # → /tmp/audit.json
   ```

### Relative Path Anchoring

All relative paths resolve against `resolved_paths.repo_root`, **not** the current working directory.

### Default Locations

Default output paths (where `<tool_home>` = `<repo_root>/.ratchetr`):

- Manifest: `<tool_home>/manifest.json`
- Dashboard JSON: `<tool_home>/dashboard.json`
- Dashboard Markdown: `<tool_home>/dashboard.md`
- Dashboard HTML: `<tool_home>/dashboard.html`
- Ratchet file: `<repo_root>/ratchet.json`
- Cache: `<tool_home>/.cache`
- Logs: `<tool_home>/logs`

---

## Precedence Chain Summary

**Global Precedence Rule:**

```text
CLI flags > Environment variables > Config file > Defaults
```

### Specific Chains

#### Repository Root

```text
--root > RATCHETR_ROOT > discovery via markers (ratchetr.toml, .ratchetr.toml, pyproject.toml)
```

#### Tool Home

```text
--ratchetr-dir > RATCHETR_DIR > config paths.ratchetr_dir > <root>/.ratchetr
```

#### Manifest Path

```text
--manifest > RATCHETR_MANIFEST > config audit.manifest_path > <tool_home>/manifest.json
```

#### Cache Directory

```text
--cache-dir > RATCHETR_CACHE_DIR > config paths.cache_dir > <tool_home>/.cache
```

#### Log Directory

```text
--log-dir > RATCHETR_LOG_DIR > config paths.log_dir > <tool_home>/logs
```

#### Dashboard Outputs

```text
--dashboard FORMAT:PATH > config audit.dashboard_{format} > <tool_home>/dashboard.{format}
```

#### Audit Scope (CURRENT vs TARGET)

**CURRENT mode:**

```text
CLI positional args > RATCHETR_INCLUDE > config audit.default_include > ["."]
```

**TARGET mode:**

```text
RATCHETR_INCLUDE > config audit.default_include > ["."]
(CLI positional args DO NOT participate in TARGET)
```

---

## Mode Semantics (CURRENT vs TARGET)

### Contract Requirement

> CLI positional scope participates only in CURRENT. TARGET scope is resolved from env/config/default.

### Behavior

- `rtr audit src tests` → CURRENT scans `src/`, `tests/`; TARGET scans from env/config/default
- `rtr audit --mode target` → TARGET only, scans from env/config/default
- `rtr audit --mode current src` → CURRENT only, scans `src/`

### Per-Engine Deduplication

Deduplication is **plan-based** and **per-engine**:

- If CURRENT and TARGET plans are equivalent for an engine → run TARGET only (canonical)
- Plan equivalence considers: targets, args, profile, config, enablement
- Ordering differences are canonicalized (sorted) before comparison
- Deselected engines (explicit empty `default_include`) are not executed

---

## Engine Error vs Diagnostic Distinction

### Engine Errors

Failures in tool execution itself (distinct from code diagnostics):

- Tool not found or not executable
- JSON parsing failure from tool output
- Non-zero exit code with no parseable output
- Tool crash or timeout

**Behavior:**

- Logged with severity `ERROR` or `CRITICAL`
- Reported separately from code diagnostics
- **Not counted** in issue totals (errors/warnings/info)
- Captured in `RunResult.engine_error` field
- Always trigger non-zero exit, regardless of `--fail-on`

### Dashboard Presentation

Engine failures appear in a dedicated section:

```markdown
## Engine Execution Failures

- **pyright**: JSON parse error (exit code 1)
- **mypy**: Command not found
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error (invalid arguments, file not found, etc.) |
| `2` | Audit failure (diagnostics exceed `--fail-on` threshold or engine execution failed) |

### `--fail-on` Policy

Controls when code diagnostics trigger non-zero exit:

- `never` / `none` → Always exit 0 (unless engine failures)
- `errors` → Exit 2 if any severity=error diagnostics found
- `warnings` → Exit 2 if errors or warnings found
- `any` → Exit 2 if any diagnostics found (including info)

**Note:** Engine failures always trigger exit code 2, regardless of `--fail-on`.

---

## Flag Type Reference

- **flag**: Boolean, present or absent (e.g., `--dry-run`)
- **option**: Single value (e.g., `--root PATH`)
- **choice**: Restricted set of values (e.g., `--mode {current,target}`)
- **repeatable**: Can be specified multiple times (e.g., `--runner pyright --runner mypy`)
- **special**: Custom parser (e.g., `--readiness level=strict limit=10`)

---

## Related Documentation

- [CLI Contract](contract.md) - Authoritative behavior specification
- [CLI Overview](overview.md) - Command examples and workflows
- [Configuration Guide](../configuration.md) - Config file reference
