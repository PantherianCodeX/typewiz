# ratchetr Roadmap

This document outlines the development roadmap for ratchetr, a universal typing & static-analysis aggregator.

For current usage and features, see [README.md](README.md).

## Current Status: Alpha (v0.1.x)

ratchetr is in **alpha** status. APIs, CLI flags, and dashboards may change without deprecation, but schemas and error codes are converging toward stability.

---

## Implemented Features

### Core Infrastructure ✅

- **Engine abstraction layer** with pluggable architecture
- **Builtin engines**: mypy and pyright with full integration
- **Plugin discovery** via entry points (`ratchetr.engines`)
- **Manifest builder** with strict JSON Schema validation (`schemaVersion: "1"`)
- **Dashboard system** with JSON, Markdown, and HTML outputs
- **Incremental caching** keyed on file fingerprints and engine flags

### Configuration & Profiles ✅

- **Config layering**: Project config (`ratchetr.toml`) with Pydantic 2 validation
- **Named profiles** per engine (e.g., `pyright.strict`, `mypy.incremental`)
- **Profile inheritance** for customization (base profile + overrides)
- **Directory overrides** via `ratchetr.dir.toml` for per-folder configuration
- **Engine-specific settings**: plugin args, config files, include/exclude directives

### Ratcheting System ✅

- **Per-file ratchet budgets** with severity targets
- **Engine signature tracking** to detect configuration drift
- **Ratchet workflows**: init, check, update, info, rebaseline-signature
- **Schema-backed ratchet format** (`ratchet.schema.json`)

### CLI & Workflows ✅

- **Comprehensive CLI**: audit, dashboard, query, ratchet, engines, cache, manifest, readiness, init
- **Query subsystem** for manifest exploration (overview, hotspots, readiness, runs, engines, rules)
- **Structured logging** with text and JSON formats
- **CI/CD integration** with exit codes and comparison deltas

### Quality & Standards ✅

- **Strict typing**: mypy and pyright in strict mode
- **High test coverage**: ≥95% enforced via coverage gates
- **Code quality**: Ruff, Pylint, Bandit integration
- **Tox and Makefile** workflows for standardized development

---

## In Progress (v0.1.x → v0.2.0)

### Foundation Hardening

- [ ] Make CLI outputs idempotent (rewrite dashboards even when files exist)
- [ ] Generalize project-root discovery beyond `pyrightconfig.json`
- [ ] Surface clearer errors for configuration issues
- [ ] Tighten engine command construction with richer typing and validation hooks

### Dashboard Experience

- [ ] Optimize dashboard rendering for large manifests (>10k diagnostics)
- [ ] Add sorting and filtering controls to HTML dashboards
- [ ] Enhance readiness categorization with severity-based filtering
- [ ] Improve mobile/responsive layout for HTML dashboards

---

## Planned Features

### v0.2.0 - Enhanced Ratcheting & Tooling (Target: Q2 2026)

#### Ratchet Improvements

- [ ] **Per-rule budgets**: Track and ratchet down specific diagnostic codes
- [ ] **Per-signature budgets**: Use content-based signatures for stable issue tracking across file changes
- [ ] **Line-level ratchets**: Ratchet at line granularity for precise regression tracking
- [ ] **Baseline comparison views**: Dashboard visualizations showing ratchet progress over time

#### Additional Engines

- [ ] **Pylint integration**: Add pylint as builtin engine with profile support
- [ ] **Ruff integration**: Support Ruff's type checking capabilities
- [ ] **Engine templates**: Provide scaffolding for common external tools

#### Developer Experience

- [ ] **VS Code extension**: Tasks and problem matchers for ratchetr workflows
- [ ] **Pre-commit hooks**: Official pre-commit integration for ratchet checks
- [ ] **Watch mode**: `ratchetr audit --watch` for live feedback during development

---

### v0.3.0 - Cross-Language Support (Target: Q3 2026)

#### Multi-Language Engines

- [ ] **TypeScript/ESLint**: Extend engine architecture to JavaScript/TypeScript
- [ ] **Kotlin/ktlint**: Support JVM languages
- [ ] **C++/clang-tidy**: Support native languages
- [ ] **Language-agnostic manifest schema**: Generalize beyond Python-specific diagnostics

#### Workspace Features

- [ ] **Monorepo support**: Per-package ratchets and dashboards with workspace aggregation
- [ ] **Cross-project dependencies**: Track typing completeness across package boundaries
- [ ] **Incremental analysis**: Only re-analyze changed packages in large workspaces

---

### v0.4.0 - Advanced Analytics & Integrations (Target: Q4 2026)

#### Analytics & Insights

- [ ] **Trend analysis**: Track typing health metrics over time
- [ ] **Team dashboards**: Per-team/per-package ownership and progress tracking
- [ ] **Technical debt scoring**: Quantify typing debt and estimate remediation effort
- [ ] **Hotspot prediction**: ML-based prediction of future error-prone areas

#### CI/CD Integrations

- [ ] **GitHub Actions**: Official action for pull request comments and status checks
- [ ] **GitLab CI templates**: Pre-built pipelines for common workflows
- [ ] **Jenkins plugin**: Native Jenkins integration
- [ ] **Slack/Discord notifications**: Ratchet breach alerts and progress updates

#### External Tool Integration

- [ ] **IDE language servers**: Provide ratchetr diagnostics via LSP
- [ ] **Code review tools**: Integrate ratchet checks into review workflows
- [ ] **Project management**: Export typing debt to Jira, Linear, etc.

---

### Future Exploration (v1.0+)

#### Enterprise Features

- [ ] **License key management**: Enhanced licensing system for commercial use
- [ ] **Centralized dashboards**: Multi-repo aggregation and org-wide views
- [ ] **Custom rule engines**: Allow organizations to define custom diagnostic rules
- [ ] **Audit logs**: Track configuration changes and ratchet modifications

#### Advanced Engine Capabilities

- [ ] **Pyre integration**: Support Meta's Pyre type checker
- [ ] **Pytype integration**: Support Google's Pytype checker
- [ ] **Custom parsers**: Allow custom diagnostic parsers for proprietary tools
- [ ] **Engine orchestration**: Parallel engine execution with dependency resolution

#### API & SDK

- [ ] **HTTP API**: Remote manifest querying and ratchet checking
- [ ] **Python SDK**: Programmatic access to all CLI functionality
- [ ] **Webhooks**: Event-driven integrations for manifest updates

---

## Schema Stability Commitment

Starting with v0.2.0, we commit to:

1. **Manifest schema (`schemaVersion: "1"`)**: No breaking changes; additive-only updates
2. **Ratchet schema**: Backward-compatible updates with migration tools
3. **Error codes**: Stable codes with deprecation warnings (6-month notice)

Breaking schema changes will increment the major version (v1.0, v2.0, etc.).

---

## Contributing to the Roadmap

We welcome feedback on roadmap priorities! To suggest features:

1. **Check existing issues**: Search [GitHub Issues](https://github.com/CrownOps/ratchetr/issues)
2. **Open a feature request**: Use the "Feature Request" template
3. **Discuss in proposals**: Large features may require RFC-style proposals

For commercial licensing or sponsored feature development, contact **<pantheriancodex@pm.me>**.

---

## Version History

- **v0.1.0** (2025-12-07): Initial alpha release
  - Core engine abstraction, builtin mypy/pyright
  - Manifest builder, dashboard system, ratcheting
  - Plugin architecture, CLI workflows, strict typing
