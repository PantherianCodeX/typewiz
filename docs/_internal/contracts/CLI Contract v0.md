# ratchetr CLI Contract

> Contract for CLI behavior — PRs are measured against this specification

This document defines the authoritative behavior contract for the `ratchetr` CLI. All implementation changes must conform to this specification.

## 1. Root SSOT (Single Source of Truth)

### Behavior

The repository root is discovered exactly **once** during CLI context initialization in `build_cli_context()` via `resolve_paths()`. Once resolved, the root flows through the system as `context.resolved_paths.repo_root` and is never rediscovered.

### Precedence

Root resolution follows this strict precedence chain:

1. **CLI override**: `--root PATH`
2. **Environment variable**: `RATCHETR_ROOT`
3. **Auto-discovery**: Walk parent directories looking for markers

Discovery markers (in order):

- `ratchetr.toml`
- `.ratchetr.toml`
- `pyproject.toml`

### Path Anchoring

All artifact paths are anchored to the resolved root:

- Tool home defaults to `<root>/.ratchetr`
- Manifest defaults to `<tool_home>/manifest.json`
- Dashboard outputs default to `<tool_home>/dashboard.{json,md,html}`
- Cache defaults to `<tool_home>/.cache`
- Logs default to `<tool_home>/logs`

Relative paths in configuration files are resolved **relative to the repo root**.

### Example

```bash
# Override root to a subdirectory
rtr audit --root ./packages/core

# All outputs land under ./packages/core/.ratchetr/
# Config discovery searches from ./packages/core/
```

## 2. Output Grammar

### Manifest Outputs

**Flag**: `--save-as FORMAT[:PATH]`

**Alias**: `-s`

**Usage**:

- Repeatable flag (each occurrence takes exactly one `FORMAT[:PATH]` value)
- Manifest format: `json` only (manifests are structured data, not multi-format)
- Default path: `<tool_home>/manifest.json`

**Path Resolution**:

The optional `:PATH` component supports intuitive directory vs. file semantics:

1. **Omitted** → default filename at default location
2. **`directory/`** → default filename in specified directory (trailing `/` required)
3. **`filename.ext`** → specified filename (relative to root)
4. **`/abs/path/`** → default filename in absolute directory (trailing `/` required)
5. **`/abs/path/file.ext`** → absolute file path

**Examples**:

```bash
# Default location
rtr audit --save-as json
# → .ratchetr/manifest.json

# Custom directory (trailing / signals directory)
rtr audit --save-as json:reports/
# → reports/manifest.json

# Custom filename
rtr audit --save-as json:reports/audit-2024.json
# → reports/audit-2024.json

# Absolute directory
rtr audit --save-as json:/tmp/
# → /tmp/manifest.json

# Absolute file path
rtr audit --save-as json:/tmp/project-audit.json
# → /tmp/project-audit.json
```

### Dashboard Outputs

**Flag**: `--dashboard FORMAT[:PATH]`

**Alias**: `-d`

**Usage**:

- Repeatable flag (each occurrence takes exactly one `FORMAT[:PATH]` value)
- Formats: `json`, `markdown`, `html`
- Default paths:
  - JSON: `<tool_home>/dashboard.json`
  - Markdown: `<tool_home>/dashboard.md`
  - HTML: `<tool_home>/dashboard.html`

**Path Resolution** (same semantics as `--save-as`):

1. **Omitted** → format-specific default filename at default location
2. **`directory/`** → format-specific default filename in directory (trailing `/`)
3. **`filename.ext`** → specified filename (relative to root)
4. **`/abs/path/`** → format-specific default in absolute directory (trailing `/`)
5. **`/abs/path/file.ext`** → absolute file path

**Examples**:

```bash
# Single format, default location
rtr audit --dashboard html
# → .ratchetr/dashboard.html

# Multiple formats with defaults
rtr audit --dashboard json --dashboard markdown --dashboard html
# → .ratchetr/dashboard.json
# → .ratchetr/dashboard.md
# → .ratchetr/dashboard.html

# Custom directory for HTML (trailing / signals directory)
rtr audit --dashboard html:site/
# → site/dashboard.html

# Custom filename for HTML
rtr audit --dashboard html:site/index.html
# → site/index.html

# Mix of defaults and custom paths
rtr audit --dashboard json --dashboard html:docs/typing/
# → .ratchetr/dashboard.json
# → docs/typing/dashboard.html
```

### Path Resolution

- **Absolute paths**: Used as-is
- **Relative paths**: Resolved against `repo_root`
- **Trailing `/`**: Unambiguous directory signal (OS-independent)
  - `reports/` → directory, use format-specific default filename
  - `reports/custom.html` → file path
  - Works consistently on Windows, macOS, Linux

**Rationale**: Trailing `/` provides deterministic, intuitive semantics with no magic or guessing. Easy to learn through trial and error.

## 3. Scope Rules

### Include Scope

Positional arguments specify directories to include in the audit:

```bash
rtr audit src tests
```

This scans `src/` and `tests/` directories.

### Precedence

Scope determination follows this precedence:

1. **CLI positional args**: Override all other scope settings
2. **Environment variable**: `RATCHETR_INCLUDE`
3. **Config `include_paths`/`exclude_paths`**: From `ratchetr.toml` `[audit]` or `pyproject.toml` `[tool.ratchetr.audit]`
4. **NO Auto-detection**: Defaults to `["."]` (scan everything from root).

### Example

```toml
# ratchetr.toml
[audit]
includes = ["src", "lib", "tests", "scripts/foo.py"]
```

```bash
# Config specifies ["src", "lib", "tests", "scripts/foo.py"]
rtr audit
# Scans: src/, lib/, tests/ directories and scripts/foo.py file

# CLI overrides config
rtr audit tests
# Scans: tests/ only
```

## 4. Precedence Chain

### Global Precedence

All settings follow this hierarchy:
**CLI flags > Environment variables > Config file > Defaults**

### Specific Precedence Chains

#### Repository Root

```text
--root > RATCHETR_ROOT > discovery via markers
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

### Environment Variables

All path-related environment variables:

- `RATCHETR_ROOT` - Repository root override
- `RATCHETR_CONFIG` - Config file path override
- `RATCHETR_DIR` - Tool home directory override
- `RATCHETR_MANIFEST` - Manifest file path override
- `RATCHETR_CACHE_DIR` - Cache directory override
- `RATCHETR_LOG_DIR` - Log directory override
- `RATCHETR_INCLUDE` - JSON string array: List of files/folders to scan

### Example

```bash
# Set root via environment
export RATCHETR_ROOT=/path/to/project

# CLI override takes precedence
rtr audit --root /different/path

# Uses: /different/path (CLI wins)
```

## 5. Dashboard Outputs

### Output Formats

Three dashboard formats are supported:

1. **JSON** - Machine-readable structured data
2. **Markdown** - Human-readable summary
3. **HTML** - Interactive web dashboard

### Default Locations

When no custom path is specified:

- JSON: `<tool_home>/dashboard.json`
- Markdown: `<tool_home>/dashboard.md`
- HTML: `<tool_home>/dashboard.html`

Where `<tool_home>` defaults to `<root>/.ratchetr`.

### Multi-Format Output

Multiple dashboard formats can be generated in a single run:

```bash
rtr audit --dashboard json --dashboard markdown --dashboard html
```

This produces all three formats at their default locations.

### Custom Paths

Custom output paths can be specified per format:

```bash
rtr audit --dashboard html:docs/typing-report.html
```

Relative paths resolve against the repository root.

### Dashboard Content

Dashboards contain:

- **Summary statistics**: Total files scanned, error/warning counts by severity
- **Per-file breakdown**: Diagnostics organized by file path
- **Engine metadata**: Tool versions, runtime information
- **Ratchet status**: Current budgets vs. baseline (if applicable)

Dashboards do **not** include engine execution failures (see section 6).

## 6. Engine Errors

### Definition

**Engine errors** are failures in tool execution itself, distinct from code diagnostics reported by the tool.

Examples:

- Tool not found or not executable
- JSON parsing failure from tool output
- Non-zero exit code with no parseable output
- Tool crash or timeout

### Reporting

Engine errors are:

- Logged with severity `ERROR` or `CRITICAL`
- Reported separately from code diagnostics
- **Not counted** in issue totals (errors/warnings/info)
- Captured in `RunResult.engine_error` field

### Dashboard Presentation

Dashboards show engine failures in a dedicated section:

```markdown
## Engine Execution Failures

- **pyright**: JSON parse error (exit code 1)
- **mypy**: Command not found
```

These failures appear **before** the diagnostic breakdown and are visually distinguished.

### Exit Codes

When engine execution fails:

- CLI returns non-zero exit code (typically 2)
- Error details are logged to stderr
- Partial results from successful engines are still produced

### `--fail-on` Policy

The `--fail-on` flag controls when code diagnostics trigger non-zero exit:

- `never` or `none` - Always exit 0 (unless engine failures)
- `errors` - Exit non-zero if any severity=error diagnostics found
- `warnings` - Exit non-zero if errors or warnings found
- `any` - Exit non-zero if any diagnostics found (including info)

**Note**: Engine failures always trigger non-zero exit, regardless of `--fail-on`.

## Canonical Command Examples

### Basic Audit

```bash
# Audit with default settings
rtr audit

# Scans auto-detected paths
# Outputs: .ratchetr/manifest.json
```

### Multi-Format Outputs

```bash
# With short aliases and --exclude flag
rtr audit -s json -s markdown \
          -d json -d html:site/ \
          src tests

# Scans: src/, tests/
# Manifest outputs:
#   - .ratchetr/manifest.json
#   - .ratchetr/manifest.md
# Dashboard outputs:
#   - .ratchetr/dashboard.json
#   - site/dashboard.html

# Long form also supported
rtr audit --save-as json --save-as markdown \
          --dashboard json --dashboard html:site/index.html \
          src tests

# Scans: src/, tests/
# Manifest outputs:
#   - .ratchetr/manifest.json
#   - .ratchetr/manifest.md
# Dashboard outputs:
#   - .ratchetr/dashboard.json
#   - site/index.html
```

### Root Override

```bash
# Override repository root
rtr audit --root ./packages/core

# All operations relative to ./packages/core:
# - Config discovery searches from ./packages/core/
# - Outputs land in ./packages/core/.ratchetr/
# - Scope paths resolved from ./packages/core/
```

### Environment-Based Configuration

```bash
# Set root via environment
export RATCHETR_ROOT=/path/to/project

# Run audit (uses environment root)
rtr audit

# CLI override takes precedence
rtr audit --root /different/path
```

### Scope Precedence

```bash
# With config specifying include_paths = ["src", "lib"]

# Use config scope
rtr audit
# Scans: src/, lib/

# CLI overrides config
rtr audit tests docs
# Scans: tests/, docs/ (ignores config)
```

## Filesystem Layout Examples

### Default Layout

With `--root .` (current directory):

```text
.
├── .ratchetr/
│   ├── .cache/          # Engine cache
│   ├── logs/            # Log files
│   ├── manifest.json    # Default manifest output
│   ├── dashboard.json   # Dashboard JSON
│   ├── dashboard.md     # Dashboard Markdown
│   └── dashboard.html   # Dashboard HTML
├── ratchetr.toml        # Config file
├── src/
└── tests/
```

### Root Override

With `--root src`:

```text
.
├── src/
│   ├── .ratchetr/       # Outputs land here
│   │   ├── manifest.json
│   │   ├── dashboard.json
│   │   ├── dashboard.md
│   │   └── dashboard.html
│   ├── ratchetr.toml    # Config searched from src/
│   └── ...
└── tests/
```

### Custom Output Paths

With `--dashboard html:reports/site/`:

```text
.
├── .ratchetr/
│   ├── manifest.json
│   ├── dashboard.json   # Default JSON location
│   └── dashboard.md     # Default Markdown location
├── reports/
│   └── site/
│       └── index.html   # Custom HTML location
└── src/
```

### Determining file or folder?

For explicit filesystem paths (e.g., positional discovery inputs and output targets), ratchetr treats a value as a file unless it ends with /. If a non-/ path does not exist as a file, it may be treated as a directory input for discovery.

## Implementation Notes

### Phase Implementation

This contract is implemented across multiple PRs:

- **PR A** (this doc): Contract documentation
- **PR B**: Root SSOT enforcement (eliminate redundant discovery)
- **PR C**: CLI grammar updates (`-s`/`-d` aliases)
- **PR D**: Scope precedence (remove heuristics, implement chain)
- **PR E**: Single persistence pathway (unified dashboard writer)
- **PR F**: Engine execution standardization and error handling
- **PR G**: End-to-end wiring, tests, and documentation

### Version

This contract is for `ratchetr` version `0.1.x` (alpha). APIs and CLI flags may change without deprecation, but this contract establishes the target behavior.

### Related Documentation

- [`docs/cli/overview.md`](overview.md) - CLI overview and command list
- [`docs/cli/manifest.md`](manifest.md) - Manifest format and tooling
- [`docs/cli/ratchet.md`](ratchet.md) - Ratchet budget management
- [`docs/ratchetr.md`](../ratchetr.md) - Architecture overview
- [`examples/ratchetr.sample.toml`](../../examples/ratchetr.sample.toml) - Configuration examples
