# ratchetr Alpha Release & Documentation Plan

This document captures the working plan for preparing ratchetr for a clear, alpha-quality `0.1.x` release with best-practice packaging and documentation.

**Status**: Ready for execution

**Target**: Clean alpha release with consistent messaging and improved documentation

**Scope**: Documentation and packaging improvements (no code changes beyond metadata)

---

## Execution Strategy

### Prerequisites

- [ ] Create backup branch: `git checkout -b pre-docs-overhaul-backup`
- [ ] Return to main: `git checkout main`
- [ ] Ensure clean working directory: `git status`

### Execution Phases

**Phase 1: Foundation** (Sequential - ~1 hour)

- Packaging metadata updates
- Repository hygiene
- CHANGELOG expansion

**Phase 2: Documentation Core** (Can parallelize - ~2-3 hours)

- README incremental updates
- CONTRIBUTING consolidation
- ROADMAP integration

**Phase 3: Examples & Domain Docs** (Can parallelize - ~2 hours)

- Example projects creation
- CLI topics audit

**Phase 4: Verification** (Sequential - ~30 min)

- Full validation checklist
- CI verification
- Package build test

---

## 1. Release Maturity: Alpha Classification

**Goal**: Consistently communicate alpha status across all documentation.

**Rationale**: The project has:

- Installable package with `pyproject.toml`, wheels/sdists, CLI entry points
- Coherent CLI surface (8+ commands) with topic documentation
- Core concepts implemented (engines, manifest, dashboard, ratchet)
- Strict typing + high test coverage (≥95%)
- JSON schemas, but APIs may still change

**Wording standard**: "**Alpha-quality 0.1.x** — APIs, CLI flags, and dashboards may change without deprecation, but schemas and error codes are converging."

### Actions

- [ ] Update `pyproject.toml` line 14: Change `"Development Status :: 4 - Beta"` to `"Development Status :: 3 - Alpha"`
- [ ] Verify no "beta" or "pre-alpha" references in docs: `grep -ri "beta\|pre-alpha" README.md docs/*.md CHANGELOG.md`
- [ ] Add alpha status callout to README.md after line 6 (see Section 3 for content)

**Validation**:

- [ ] `grep "Alpha" pyproject.toml README.md` shows consistent messaging
- [ ] No conflicting status indicators found

---

## 2. Packaging & Metadata Best Practices

**Goal**: Clean up dependencies and document release process.

### Actions

#### A. Dependencies Cleanup

- [ ] Move `pre-commit` from `project.dependencies` (line 27) to `requirements-dev.txt`
- [ ] Verify runtime dependencies are minimal: `pyright`, `mypy`, `pydantic` only
- [ ] Test installation: `make package.build && make package.install-test`

#### B. Release Process Documentation

- [ ] Add "Release Process" section to CONTRIBUTING.md (see template below)
- [ ] Confirm `requires-python = ">=3.12"` in pyproject.toml (line 10)
- [ ] Verify all docs reference Python 3.12+ consistently

**Release Process Template for CONTRIBUTING.md**:

```markdown
## Release Process

1. **Version Bump**: Update `version` in `pyproject.toml`
2. **CHANGELOG**: Add entry under `## Unreleased` with changes
3. **Pre-release Validation**:
   - Run `make ci.check` (all gates must pass)
   - Run `make package.build && make package.check`
4. **Git Tagging**: Create annotated tag `git tag -a v0.1.x -m "Release v0.1.x"`
5. **Build Artifacts**: `make package.build`
6. **Publication**: (Process TBD for first public release)
```

**Validation**:

- [ ] Package installs without pre-commit: `pip install dist/*.whl && ratchetr --help`
- [ ] CONTRIBUTING.md has release section

---

## 3. README.md: Incremental Alpha Updates

**Goal**: Add alpha status, limitations, and roadmap without full rewrite.

**Strategy**: Incremental additions to existing solid README structure.

### Actions

#### A. Alpha Status Callout (HIGH PRIORITY)

- [ ] Add after line 6 (after status line):

```markdown
## ⚠️ Alpha Status

ratchetr is **alpha-quality software (v0.1.x)**. While the core functionality is solid and tested, expect:

- API and CLI changes between minor versions
- Dashboard layouts and features evolving
- Schemas stabilizing but not yet guaranteed stable

Production use is supported under commercial license, but be prepared for updates. See [ROADMAP.md](ROADMAP.md) for stability commitments.
```

#### B. Limitations Section (HIGH PRIORITY)

- [ ] Add before "Licensing & Commercial Use" section (before line 202):

```markdown
## Limitations (Alpha)

Current alpha limitations:

- **Python-only engines**: Only mypy and pyright built-in (other languages planned for v0.3.0+)
- **File-level ratchets**: Budgets track per-file counts; per-rule and per-signature ratchets coming in v0.2.0
- **Dashboard optimization**: HTML dashboards work best with <10k diagnostics; large manifest support improving
- **Schema evolution**: `schemaVersion: "1"` is stabilizing but may have additive changes in 0.1.x releases

See [ROADMAP.md](ROADMAP.md) for planned improvements.
```

#### C. Roadmap Section Update

- [ ] Replace "Roadmap" section (lines 518-543) with:

```markdown
## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development roadmap.

**Next milestones**:

- **v0.2.0**: Per-rule/per-signature ratchets, additional engines (Pylint, Ruff), VS Code extension
- **v0.3.0**: Cross-language support (TypeScript, Kotlin, C++), monorepo features
- **v1.0+**: Enterprise features, advanced analytics, HTTP API
```

#### D. Architecture Cross-Reference

- [ ] Add after "Features" section (after line 15):

```markdown
### Architecture

ratchetr follows a **schema-first, plugin-friendly** design:

- **Engines** (builtin or plugins) produce diagnostics
- **Manifest builder** aggregates results with strict JSON Schema validation
- **Dashboard system** renders summaries (JSON/Markdown/HTML)
- **Ratchet system** enforces per-file budgets with signature tracking

For deep-dive architecture documentation, see [docs/ratchetr.md](docs/ratchetr.md).
```

**Validation**:

- [ ] Alpha status appears prominently in README
- [ ] All cross-references valid: ROADMAP.md and docs/ratchetr.md exist
- [ ] No contradictions with ROADMAP.md

---

## 4. docs/ratchetr.md: Architecture Deep Dive

**Goal**: Improve structure without complete rewrite.

**Note**: LOWER PRIORITY. Existing doc is functional; focus on higher-value items first.

### Actions (If Time Permits)

- [ ] Remove duplicate "how to run" content (lines 8-50 already covered in README)
- [ ] Add "Design Principles" subsection under introduction
- [ ] Add "Module Map" section with brief module descriptions
- [ ] Add cross-links to CLI topics, examples, and schemas

**Validation**:

- [ ] No duplicate content with README
- [ ] All cross-links valid

---

## 5. CONTRIBUTING & Standards Consolidation

**Goal**: Single canonical CONTRIBUTING.md at repo root with consolidated standards.

### Actions

#### A. Move and Update CONTRIBUTING

- [ ] Ensure `CONTRIBUTING.md` exists at repository root
- [ ] Update all references to CONTRIBUTING path: `grep -r "CONTRIBUTING.md" . --include="*.md"`
- [ ] Add "Release Process" section from Section 2B above
- [ ] Add versioning policy (see template below)

**Versioning Policy Template**:

```markdown
## Versioning & Stability

ratchetr follows **semantic versioning** with alpha-specific semantics:

- **0.y.z-alpha**: Breaking changes allowed between minor versions
- **Schema stability**: `schemaVersion: "1"` aims for additive-only changes
- **Error codes**: Stable once documented; deprecation warnings for 6 months before removal
- **CLI flags**: May change without deprecation in 0.y.z; deprecation warnings start at v1.0+

See [ROADMAP.md](ROADMAP.md) for stability commitments per version.
```

#### B. Extract and Archive Planning Docs

- [ ] Create `docs/archive/` directory
- [ ] Review and extract durable content from planning docs to CONTRIBUTING.md
- [ ] Move planning docs to archive:

```bash
git mv STANDARDS_ENHANCEMENT_SUMMARY.md docs/archive/
git mv TEST_REFORM.md docs/archive/
git mv TEST_REORGANIZATION_ANALYSIS.md docs/archive/
```

- [ ] Add `docs/archive/README.md` explaining these are historical planning documents

**Validation**:

- [ ] `./CONTRIBUTING.md` exists and is complete
- [ ] Planning docs archived (not deleted)
- [ ] All cross-references updated

---

## 6. Domain Docs: CLI Topics Audit

**Goal**: Ensure existing CLI topic docs are accurate.

**Decision**: Use existing `docs/cli/topics/*.md` rather than creating duplicate standalone docs.

### Actions

#### A. Audit Existing CLI Topics

- [ ] Review `docs/cli/topics/manifest.md` for accuracy and current CLI flags
- [ ] Review `docs/cli/topics/ratchet.md` and add alpha limitations note
- [ ] Review `docs/cli/topics/plugins.md` for consistent "engine" terminology
- [ ] Review `docs/cli/topics/overview.md` to reflect alpha status
- [ ] Review `docs/cli/topics/query.md` for complete subcommand documentation
- [ ] Replace any `ratchetr.plugins` references with `ratchetr.engines`

#### B. Add Cross-References

- [ ] Ensure each CLI topic links to related topics and examples
- [ ] Link to main architecture doc (docs/ratchetr.md) where appropriate

**Validation**:

- [ ] No references to `ratchetr.plugins` package
- [ ] All CLI commands/flags match `ratchetr <command> --help` output
- [ ] Cross-references valid

---

## 7. Examples: Create Minimal Working Projects

**Goal**: Provide runnable examples that demonstrate basic usage.

### Actions

#### A. Create examples/mypy-project/

- [ ] Create directory structure with src/example_pkg/
- [ ] Write `typing_demo.py` with intentional mypy diagnostic
- [ ] Write `mypy.ini` with strict=true
- [ ] Write `ratchetr.toml` configured for mypy runner
- [ ] Write `README.md` with installation and usage instructions
- [ ] **VALIDATE**: `cd examples/mypy-project && ratchetr audit src --manifest typing_audit.json`

#### B. Create examples/pyright-project/

- [ ] Create directory structure with src/example_pkg/
- [ ] Write `typing_demo.py` with intentional pyright diagnostic
- [ ] Write `pyrightconfig.json` with strict mode
- [ ] Write `ratchetr.toml` configured for pyright runner
- [ ] Write `README.md` with setup and usage
- [ ] **VALIDATE**: `cd examples/pyright-project && ratchetr audit src --manifest typing_audit.json`

#### C. Update Examples Index

- [ ] Verify `examples/ratchetr.sample.toml` matches current config schema
- [ ] Create `examples/README.md` listing all examples

**Validation**:

- [ ] Both example projects run successfully
- [ ] Generated manifests are valid
- [ ] READMEs are clear and complete

---

## 8. Repository Hygiene

**Goal**: Clean repository surface and ensure proper .gitignore.

### Actions

#### A. Update .gitignore

- [ ] Verify .gitignore includes all build artifacts and caches

#### B. Remove Committed Artifacts

- [ ] Check for artifacts: `git ls-files | grep -E '(coverage\.json|coverage\.xml|dist/)'`
- [ ] Remove if found: `git rm --cached <file>` and commit

#### C. Archive Planning Docs

- [ ] Planning docs moved to `docs/archive/` (not deleted)

**Validation**:

- [ ] No build artifacts in git
- [ ] .gitignore prevents future commits of artifacts

---

## 9. CHANGELOG & Versioning

**Goal**: Expand CHANGELOG to reflect full alpha feature set.

### Actions

#### A. Expand v0.1.0 Entry

- [ ] Replace current v0.1.0 entry with comprehensive feature list (see template in full plan)
- [ ] Include sections: Features, Quality & Standards, Architecture, Licensing

#### B. Update Unreleased Section

- [ ] Add documentation improvements
- [ ] Add packaging cleanup items
- [ ] Note repository hygiene changes

**Validation**:

- [ ] CHANGELOG accurately reflects implemented features
- [ ] Unreleased section captures doc improvements

---

## 10. Verification & Quality Gates

**Goal**: Ensure all changes are valid before considering complete.

### Actions

#### A. Documentation Validation

- [ ] All internal links valid (check README cross-references)
- [ ] CLI commands in docs are valid (spot-check with grep)
- [ ] No contradictions between README and ROADMAP
- [ ] No orphaned documentation files

#### B. Package Validation

- [ ] Full CI passes: `make ci.check`
- [ ] Package builds: `make package.build`
- [ ] Package installs: `make package.install-test`
- [ ] Examples run successfully

#### C. Content Quality

- [ ] Alpha status mentioned in: README, ROADMAP, pyproject.toml classifier
- [ ] Limitations section in README is accurate
- [ ] CHANGELOG reflects actual features
- [ ] All cross-references bidirectional where appropriate

**Validation Checklist**:

- [ ] CI green
- [ ] Package installable
- [ ] Examples functional
- [ ] Links valid
- [ ] Messaging consistent

---

## Success Criteria

The release documentation plan is complete when:

1. ✅ **Alpha status** clearly communicated in README, ROADMAP, pyproject.toml
2. ✅ **Package metadata** clean (correct classifier, dev dependencies separated)
3. ✅ **Documentation** accurate (CLI topics audited, cross-references valid)
4. ✅ **Examples** functional (mypy-project and pyright-project runnable)
5. ✅ **CHANGELOG** comprehensive (v0.1.0 reflects full feature set)
6. ✅ **CONTRIBUTING** consolidated (release process documented, planning docs archived)
7. ✅ **Repository** clean (no artifacts, proper .gitignore)
8. ✅ **CI/CD** passing (make ci.check succeeds)
9. ✅ **Package** installable (make package.install-test succeeds)

---

## Priority Guidance

### High Priority (Must-Have for Alpha)

- Section 1: Alpha classification
- Section 2: Packaging cleanup
- Section 3: README alpha callout + limitations
- Section 8: Repository hygiene
- Section 9: CHANGELOG expansion
- Section 10: Verification

### Medium Priority (Strongly Recommended)

- Section 5: CONTRIBUTING consolidation
- Section 7: Example projects
- ROADMAP.md integration into README

### Low Priority (Nice-to-Have)

- Section 4: docs/ratchetr.md restructure
- Section 6: CLI topics audit

---

## Estimated Timeline

- **Phase 1** (Foundation): 1 hour
- **Phase 2** (Documentation Core): 2-3 hours
- **Phase 3** (Examples & Audit): 2 hours
- **Phase 4** (Verification): 30 minutes
- **Total**: 5-7 hours for complete execution

---

## Commit Strategy

- One commit per section (helps with review and potential rollback)
- Descriptive commit messages: `docs: [section name] - [brief description]`
- Final commit: `docs: complete alpha release documentation plan`
