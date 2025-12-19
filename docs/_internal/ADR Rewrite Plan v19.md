# Ratchetr ADR Reorganization and Rewrite Plan (Integrated v19 — Planning Only)

**Status:** Active plan (documentation-only, including documentation-control scripts under `scripts/docs/` only)
**Date:** 2025-12-18
**Audience:** Ratchetr maintainers and contributors performing ADR rewrites and reference-doc creation
**Normative authority for rewrites:** *Ratchetr Execution and Contract Policy (vCurrent)* (user-provided)
**Supersedes:** `adr-reorg-plan-v3.md`, `ratchetr-adr-reorg-best-of-plan-2025-12-17.md`, `ADR Rewrite Plan v4.md`, `ADR Rewrite Plan v4.updated.md`, `ADR Rewrite Plan v6.md`, `ADR Rewrite Plan v7.md`, `ADR Rewrite Plan v8.md`, `ADR Rewrite Plan v9.md`, `ADR Rewrite Plan v10.md`, `ADR Rewrite Plan v11.md`, and all other rewrite plans (all are incorporated here)

**Scope note:** “Documentation-only” in this plan includes the minimal documentation tooling required to generate and validate documentation artifacts (indexes, registries, checks), but **only** within `scripts/docs/`.

This document is a workplan for reorganizing and rewriting Ratchetr’s ADR set under strict MADR principles, while relocating exhaustive specifications into tightly-scoped supplementary documents. It is intentionally “mechanically executable”: every decision domain has one owner, every phase has acceptance criteria, and every artifact has an explicit home.

---

## 0. Purpose and deliverables

### 0.1 Purpose

1. Produce a cohesive ADR set (0001–0009) where each ADR is decision-sized (MADR), internally consistent, and non-overlapping.
2. Produce supplementary documentation (reference specs and CLI contract docs) that contain the exhaustive detail ADRs must *not* contain.
3. Remove ambiguity and drift: each normative concept has exactly one canonical home and every other document links to it.

### 0.2 Deliverables covered by this plan

- Final ADR index (0001–0009) with strict scope ownership and “must-not-contain” boundaries.
- Canonical ownership matrix (enforcement map) for reviews and future contributions.
- Supplementary document set:
  - `docs/reference/*` (normative, exhaustive, testable specs)
  - `docs/cli/*` (user-facing contract, inventories, and parity tables)
  - `docs/_internal/*` (governance, archives, coherence checklist, policy snapshot, implementation notes, roadmaps)
- Mermaid diagram inventory and placement rules (one authoritative source per diagram).
- Mapping of legacy ADR drafts → new ADRs and reference docs (supersedence plan).
- Phased documentation execution plan with acceptance criteria.

---

## 1. Authority model and non-negotiables

### 1.1 Authority order

1. **Execution and Contract Policy (vCurrent)** (user-provided, locked for the rewrite).
2. **This plan** (integration and execution plan for documentation only).
3. Existing ADR drafts, CLI help snapshots, and current code **only where they do not conflict** with (1) and (2).

### 1.2 Non-negotiables (enforced by review)

- **One concept, one owner:** each normative concept has exactly one “home” ADR *or* one reference spec. Duplicate definitions are removed; non-owners link.
- **Strict MADR (enforced headings):** Every ADR must contain the five MADR headings as literal headings:
  - `Context and Problem Statement`
  - `Decision Drivers`
  - `Considered Options`
  - `Decision Outcome`
  - `Consequences`
  Additional headings are allowed only for narrowly-scoped cross-links/diagrams and must not expand scope; any additions require a brief justification in the ADR’s draft log.
- **No orphan decisions:** every decision recorded in an ADR must have an accompanying **canonical spec home** (reference spec and/or CLI contract doc) that fully specifies its operational semantics. ADRs delegate; specs/contract docs define the exhaustively testable rules.
- **Decision Drivers carry-forward:** for each rewritten ADR, carry forward the strongest Decision Drivers from its draft-2 predecessor unless they are invalidated by the Phase 0 policy snapshot. Any removal or material change is recorded in the ADR’s draft log with a rationale and policy citation.
- **No silent parameter degradation:** if any runtime-affecting input (selectors, path-like inputs, follow mode, write gating, engine parameters) cannot be applied as specified and ignoring it would change the effective configuration or scope, the run must **fail before Planning**. The failure is reported as a coded **Error Finding** and disclosed in the run summary.
- **`--manifest` is canonical (aliases: `--save-as`, `-s`):** Policy vCurrent defines `--manifest` as the canonical flag for manifest file paths (used consistently for manifest *input* and *output* wherever a manifest path is accepted). `--save-as` and `-s` are aliases with identical semantics. Contract docs must document the aliasing and record any implementation deltas in `docs/cli/parity_deltas.md`. (Alias parity enforcement tests are specified outside this plan.)
- **Policy snapshot immutability:** After Phase 0, the policy snapshot is frozen for this rewrite. Any modification requires an explicit policy revision note, an entry in the relevant draft log(s), and a plan version bump (no silent edits).
- **No flag inventories inside ADRs:** inventories, parity tables, and applicability matrices live in `docs/cli/*`.
- **Resolution happens once:** config discovery, source precedence, and merge resolution occur exactly once during **Resolution**. The result is an explicit *effective configuration/policy* object consumed by planning and runtime; later stages must not re-run precedence or discovery.
- **Canonical coordinate system:** selection and reporting use **normalized base-relative paths rendered with `/`**.
- **Selectors remain portable:** selector syntax is OS-agnostic. `\` is **literal** in selectors (never a separator).
- **Absolute paths are explicitly gated:** absolute path-like inputs are rejected unless explicitly permitted via `--allow-absolute` / `paths.allow_absolute` (names per policy).
- **Run transparency is mandatory:** every run emits the required info/run summary (minimum field set) including mode and any suppression/disablement reasons.
- **Formal run artifacts are mandatory:** runs produce a defined artifact set (run summary, findings, resolution log, and any required auxiliary artifacts) as specified in `docs/reference/run_artifacts.md`. **Artifacts are mandatory as a logical product of a run; filesystem persistence is governed separately by ADR-0007/write-gating.** When persistence is suppressed, the artifact set must still be produced (e.g., emitted to stdout and/or returned through the service boundary), and the run summary must disclose the suppression.
- **Emissions must be clear and concise:** user-visible summary fields and warnings use plain, unambiguous phrasing (e.g., “project disabled by `--project-root none`”), avoid internal jargon, and remain stable over time.
- **CLI-to-Spec normalization is boundary-only:** argv normalization (including macro expansion) occurs before constructing the command specification (\`CommandSpec\`) and never inside Resolution/Planning/Execution.
- **No needless environment inspection:** if environment is explicitly disabled (`--no-env`, including via a macro such as `--ad-hoc`), Ratchetr does not read or log environment variable values (even transiently). Run summary may disclose only that ENV was disabled and by which token.
- **Macro flags are not part of the command spec:** macro tokens (e.g., `--ad-hoc`) are expanded at the argv boundary and then removed from the normalized argv before parsing/validation. Only the expanded tokens proceed to `CommandSpec` construction.
- **Resolved values carry provenance:** effective configuration fields record their source (CLI | ENV | config | default) and relevant raw inputs; run summary discloses enabled sources and which ones contributed (without inspecting disabled sources).

### 1.3 Integrated corrections and clarifications (must be encoded in ADRs/specs)

#### 1.3.1 Current contract: POSIX path semantics (Windows path support is preserved as a promotable roadmap)

This plan adopts the current contract stance: **POSIX path semantics are normative everywhere** (CLI/ENV/config) for this rewrite set. Windows path semantics are **not** part of the normative contract at this time.

Policy anchor (required):

- This POSIX-only contract posture is taken **per Policy vCurrent**. During Phase 0, capture the exact policy section reference in the policy snapshot and mirror it here (e.g., `Policy vCurrent §<section>`).

Roadmap preservation requirements (must-do):

- Capture the full Windows path design in an **informative** roadmap document: `docs/_internal/roadmap/windows_paths.md`.
- The roadmap must be written as **promotable without refactor**: it must include the detection rules, CLI-only interpretation toggle semantics (including any OS gating if required), normalization outputs, error semantics, and provenance fields, plus how it composes with `--allow-absolute` and follow-mode traversal.

Non-foreclosure contract (must-do now):

- ADR-0006 and path reference specs must define **internal representation, provenance, identifiers/tokens, and canonical rendering** in a way that remains compatible with eventual Windows input interpretation.
- “POSIX-only” is a constraint on **parsing/interpretation of path-like inputs** today, not on the normalized path identity model. Do not encode assumptions that would later force re-architecture (e.g., assuming raw host inputs can never contain `\`, or that all host path systems share separators).
- Normative docs must not contradict the roadmap. If a future policy promotes Windows support, the roadmap should be elevatable with minimal editorial change rather than requiring conceptual rewrites.

Non-negotiable boundary that remains true now and later:

- **Selectors are portable** and never adopt OS-specific parsing rules.

#### 1.3.2 Correction: cache default naming and resolution chain

Cache defaults depend on the *resolved* `tool_home` directory name. This keeps the common defaults readable (`.ratchetr/cache`) while retaining a safe “hidden cache” fallback when `tool_home` is non-standard or user-directed. `tool_home` may be configured to any arbitrary location (including within the project root), so using a hidden cache directory name remains acceptable even when it becomes nested under a hidden directory.

Normative cache directory name rule (encode in ADR-0007 / `docs/reference/defaults.md`, referenced by `docs/reference/cache.md`):

- `cache_dirname = "cache"` if the **basename** of `tool_home` is any of: `("ratchetr", ".ratchetr")`
- otherwise `cache_dirname = ".ratchetr_cache"`

Normative cache default chain to encode in ADR-0007 / `docs/reference/cache.md`:

1. **Project Mode only:**
   1. `<tool_home>/<cache_dirname>`
   2. fallback: `<project_root>/<cache_dirname>` (only if (1) is not viable)
2. **Ad-hoc Mode, or Project Mode additional fallback:**
   1. OS user cache dir + `.ratchetr_cache`
   2. OS temp dir + `.ratchetr_cache`
3. If none viable: disable cache + emit warning Finding (and disclose in run summary)

#### 1.3.3 Tool home defaults and artifact destination taxonomy

Tool home (`tool_home`) is the canonical destination root for Ratchetr-managed outputs (artifacts, cache, logs) unless explicitly overridden.

Key requirements to encode (ADR-0007 + `docs/reference/defaults.md` + `docs/reference/artifacts.md`):

- `tool_home` is a path-like value resolved during **Resolution** (per ADR-0003) and normalized per ADR-0006.
- Default `tool_home` directory name is `.ratchetr` (location and override rules are defined in `docs/reference/defaults.md`).
- Default output destinations are children of `tool_home` (including, at minimum: cache, manifest, dashboards, and logs), with default filenames defined centrally in `docs/reference/defaults.md`.

---

## 2. Target ADR set and discrete scope boundaries

This reorg retains ADR-0001..ADR-0005 (rewritten with corrected scopes) and adds ADR-0006..ADR-0009 to keep domains discrete and prevent “mega-ADR” creep.

### 2.1 ADR index (target) with strict scope boundaries

**Titling rule (foundation ADRs):** ADR titles are short domain identifiers; subtitles carry the complete scope. Prefer clarity over cleverness. Later ADRs may have tighter titles; these foundational ADRs must be discoverable by title alone.

**Legacy-title safety note:** The archived and superseded legacy ADR-0001 through ADR-0005 drafts are being rewritten and were not implemented, but they still inform the foundation. Preserve legacy titles when referencing archived drafts.

ADR file placement and naming rules (active set):

- Active ADRs live at `docs/_internal/adr/` and use the filename pattern: `####-<kebab-title>.md` (example: `docs/_internal/adr/0003-execution-contract-foundation.md`).
- Kebab titles should match the ADR *title* (not the subtitle) and stay stable once accepted.

ADR title/subtitle rendering rules (active set):

- Each ADR uses a single H1 with the subtitle inline: `# ADR-#### <Title>: <Subtitle>` (colon + single space).
- In tables and indexes, render title and subtitle on **two lines** (title first, subtitle second) to improve scanability.

Link-update rule (critical):

- Only update links that target the **active ADR set** (per this table) and current reference docs.
- **Do not rewrite** link text or targets that intentionally reference archived ADRs.
- **All links to archived ADRs must remain valid and retain their original titles** (link text must match the archived ADR title line; do not rename archive titles).
- **Do not normalize archive references:** never change archived ADR filenames, titles, subtitles, or link text to match the new title/subtitle conventions. Archive references remain verbatim historical pointers.

Archive immutability rule (critical):

- Once a document is placed under `docs/_internal/adr/archive/`, it is **immutable**. Modifying archived documents (including ADRs) is strictly forbidden; fix references and add notes elsewhere.

| ADR | Title | Subtitle (complete scope) | Owns (decisions) | Must not contain |
| ---: | --- | --- | --- | --- |
| 0001 | Scoping Foundation | Target selection model; include/exclude selectors; selection-time evaluation | Decides the selection pipeline boundaries (selection occurs before Planning/Execution) and delegates the normative selector spec to `docs/reference/selector_semantics.md` and coded events to `docs/reference/findings.md` / `docs/reference/error_codes.md` | Full selector grammars/schemas in the ADR; path/base/project-root algorithms; link traversal rules; CLI inventories |
| 0002 | Engine Planning Foundation | Engine plan construction, merge, and normalization | Decides plan shape, merge rules, and identity invariants; delegates equivalence/dedupe dimensions, canonicalization tables, and examples to `docs/reference/engine_planning.md` and emits through `docs/reference/findings.md` / `docs/reference/error_codes.md` | Selector semantics; path/link resolution; error code decoding rules; artifact persistence rules; CLI inventories |
| 0003 | Execution Contract Foundation | Mode model; source/precedence boundaries; Resolution Domains; Runner vs Executor | Decides phase permissions (Policy vs Planning vs Execution), boundaries, and role semantics; delegates exhaustive schemas and message catalogs to reference specs | Exhaustive schemas; selector/path/link algorithms; CLI inventories |
| 0004 | Taxonomy Foundation | Canonical terminology and repository layering model | Decides canonical terms (internal and user-facing), glossary boundaries, and the repository layering model; delegates exhaustive glossary and layering diagrams to `docs/reference/taxonomy.md` | Naming rules; boundary translation rules; behavior specs; CLI inventories |
| 0005 | Naming Foundation | Repo-wide naming conventions and consistency rules | Decides naming principles and conventions (public vs internal, casing, serialization, suffix rules, and boundary translation rules); delegates exhaustive rules/examples to `docs/reference/naming_conventions.md` and default catalogs to `docs/reference/defaults.md` | Full default catalogs; behavior specs; CLI inventories |
| 0006 | Paths Foundation | Path system contract; normalization boundaries; base/project-root anchoring | Decides the path contract posture per Policy vCurrent (POSIX-only) and delegates the normative contract + resolution/representation details to `docs/reference/path_resolution.md` | Windows parsing rules (roadmap only); selector semantics; link traversal rules; CLI inventories |
| 0007 | Artifacts Foundation | Run artifacts composition vs persistence; write gating; dashboards/manifests | Decides artifact categories, write-gating rules, and the **mandated** `--manifest` canonical posture (aliases: `--save-as`, `-s`; same semantics); delegates schemas and minimum sets to `docs/reference/run_artifacts.md` / `docs/reference/run_summary.md` | Selector/path/link algorithms; exhaustive schema tables duplicated from reference specs; CLI inventories |
| 0008 | Link Traversal Foundation | Link following; boundary inclusion; link-chain provenance | Decides link-following posture and boundary inclusion rules; delegates provenance schema to `docs/reference/follow_link.md` and related specs | Path normalization algorithms (except boundary statements); CLI inventories |
| 0009 | Config Discovery Foundation | Config discovery and loading; config merge semantics; `pyproject.toml` parity | Decides config discovery/loading behavior and merge semantics **within the config source**; delegates ENV surface to `docs/reference/env_vars.md` and config load/merge details to `docs/reference/config_loading.md`. Cross-source participation/precedence is owned by ADR-0003. | ENV inventories duplicated from `env_vars.md`; cross-source precedence rules; selector/path/link algorithms; CLI inventories |

### 2.2 Canonical ownership matrix (enforcement map)

This matrix is the review guardrail used during rewrites to remove duplication. If two docs define the same concept, one is rewritten to a short reference and links to the canonical owner.

| Concept | Canonical owner |
| ---: | --- |
| Workspace vs modes; Project vs Ad-hoc | ADR-0003 |
| Source precedence; `--no-env` semantics; disclosure of disabled sources | ADR-0003 |
| CLI boundary argv normalization (macro expansion and macro-only dedup/warnings) | ADR-0003 (implementation details in `docs/_internal/cli/argv_normalization.md`) |
| Mandatory run summary contract (minimum fields) | ADR-0003 (details in `docs/reference/run_summary.md`) |
| Findings schema ownership and sources | ADR-0003 (details in `docs/reference/findings.md`) |
| Formal run artifact set (run summary, findings, resolution log) | ADR-0003 (requirement) + `docs/reference/run_artifacts.md` (normative schema and collection rules) |
| Stable identifiers and token/hash rules (e.g., `finding_id`, path tokens, `link_chain_id`) | `docs/reference/identifiers.md` (referenced by run summary/findings/follow specs) |
| Stable code registry (findings, warnings, engine failures) | `docs/reference/error_codes.md` |
| Base/project-root semantics; `^`; canonical rendering; absolute gating | ADR-0006 (details in `docs/reference/path_resolution.md`) |
| Selector semantics (targets/include/exclude; ordering; selector rejection policy; absolute gating) | `docs/reference/selector_semantics.md` (decision recorded in ADR-0001; anchors per ADR-0006) |
| Follow modes; boundary inclusion; link-chain provenance schema | ADR-0008 (details in `docs/reference/follow_link.md`) |
| Artifacts/writes policy; cache; logs | ADR-0007 (details in `docs/reference/artifacts.md` / `cache.md`) |
| Tool home resolution and artifact destination taxonomy (tool_home, cache_dir, manifest_dir, dashboard_dir, log dirs, default filenames) | ADR-0007 (defaults in `docs/reference/defaults.md`; values are loaded/merged per ADR-0009 and resolved per ADR-0006) |
| Config discovery/loading; pyproject parity; (directory overrides deferred; see §5.8) | ADR-0009 (details in `docs/reference/config_loading.md`) |
| Engine plan dedupe/equivalence and plan identity invariants | ADR-0002 (details in `docs/reference/engine_planning.md`) |
| Engine execution failure classification and reporting (`engine_error`) | `docs/reference/engine_errors.md` (referenced by run artifacts and error codes) |
| Repository layering taxonomy | ADR-0004 (details in `docs/reference/taxonomy.md`) |
| Naming rules and boundary translation | ADR-0005 (details in `docs/reference/naming_conventions.md`) |

---

## 3. Supplementary scoped documents

**Definition — “minimum viable but complete schema”:**
A schema is *minimum viable* in examples and optional surface area, but *complete* in contract: required fields and types are fully specified, stability/compatibility rules are stated, and error semantics are defined. Optional fields may be deferred only if explicitly marked as optional and forward-compatible.

To keep ADRs MADR-sized, exhaustive specs, examples, and inventories move into supplementary docs with tight scope. ADRs link to these docs rather than reproducing their content.

### 3.1 `docs/reference/*` (normative reference specs)

These documents are exhaustive and testable; they are normative specifications linked from ADRs.

Required reference specs (initial set):

- `docs/reference/identifiers.md` — canonical stable identifiers and token/hash rules used for correlation across run summaries, findings, and artifacts (includes `path_token`, `finding_id`, `link_chain_id`).
- `docs/reference/run_artifacts.md` — formal run artifact collection: **minimum required artifact set**, stability guarantees, and how run summary/findings/resolution log relate (including which content belongs in run summary vs resolution log). **Owns composition and schema; does not own persistence.** Persistence/write-gating lives in ADR-0007 and `docs/reference/artifacts.md`.
- `docs/reference/run_summary.md` — canonical run summary contract (minimum required fields, stable names, and clear, concise user-facing emissions). Must include a stable way to report:
  - base-boundary crossings (always meaningful), and
  - project-boundary crossings (meaningful only when a project boundary exists),
  with the *representation chosen and justified in this spec* (avoid guessing in the plan).
- `docs/reference/findings.md` — finding/event schema and taxonomy (diagnostics, selection-time findings, macro warnings, etc.), severity model, required metadata, and forward-compatibility rules. Finding codes are defined in `docs/reference/error_codes.md`.
- `docs/reference/error_codes.md` — canonical registry for stable codes (findings, warnings, engine failures, and other user-visible coded events). Defines code format, stability guarantees, and how per-domain documents declare codes (including aggregation rules if distributed).
- `docs/reference/engine_errors.md` — engine execution failure classification and schema (`engine_error`), including required fields and how they are emitted and included in run artifacts (distinct from diagnostics).
- `docs/reference/engine_planning.md` — engine plan equivalence dimensions, canonicalization rules/tables, and plan-shape examples (normative; referenced by ADR-0002).
- `docs/reference/path_resolution.md` — full resolution algorithm for path-like inputs (POSIX-only contract), including `^`, `base_dir`, `project_root`, allow-absolute gating, error semantics, and containment checks.
- `docs/reference/selector_semantics.md` — selector specification (grammar + parsing + canonical string form + evaluation semantics). This is the **normative** definition for selector behavior; ADR-0001 records decisions and delegates detail here.
- `docs/reference/follow_link.md` — follow modes; boundary counting; cycle detection; link-chain schema; provenance fields and examples.
- `docs/reference/artifacts.md` — artifact and write rules (behavioral policy): write gating; manifest/dashboard rules; detached suppression; collision policy. Default names/paths live in `docs/reference/defaults.md`.
- `docs/reference/defaults.md` — canonical default values and names (start of the comprehensive defaults catalog): `tool_home`, destination taxonomy (`cache_dir`, `manifest_dir`, `dashboard_dir`, log destinations), and default filenames (mode- and detached-aware).
- `docs/reference/cache.md` — cache enablement, corrected resolution chain (referencing defaults), disablement reasons, and required disclosure fields.
- `docs/reference/logs.md` — log destination rules (keying and gating), write gating, redaction expectations, and “no logs written” disclosure rules. Default names/paths live in `docs/reference/defaults.md`.
- `docs/reference/config_loading.md` — config discovery/loading, merge semantics, and `pyproject.toml` parity rules (directory overrides deferred; see §5.8).
- `docs/reference/env_vars.md` — complete environment-variable contract: inventory of supported vars, naming conventions, encoding/decoding rules (including list/JSON formats), and mapping to the underlying configuration keys. **Cross-source participation/disable/precedence rules are owned by ADR-0003**; this doc owns the ENV surface and must not redefine precedence. Config-file discovery/loading/merge remains owned by ADR-0009 and `docs/reference/config_loading.md`.
- `docs/reference/taxonomy.md` — canonical glossary and repository layering model (presentation → orchestration → domain), explicitly identifying adapter/boundary edges as first-class architectural concerns (normative; referenced by ADR-0004).
- `docs/reference/naming_conventions.md` — exhaustive naming rules plus **boundary-only translation** rules (adapters/wire mappings), including casing/serialization conventions at each boundary and the reserved-suffix contract (`*Policy/*Resolver/*Resolution/*Plan/*Executor`) (normative; referenced by ADR-0005).

Optional (add only if needed to keep ADRs small):

- `docs/reference/redaction.md` — if redaction/tokenization grows beyond a section in findings/run-summary specs.

### 3.2 `docs/cli/*` (user-facing contract and inventories)

These documents are authoritative for user-visible CLI behavior, parity, and inventories. They are not ADRs.

**Parity rule:** the documented contract may be ahead of the current CLI implementation. Any mismatch between `docs/cli/*` contract prose/flag tables and the captured help snapshots in `docs/cli/_snapshots/` must be recorded in `docs/cli/parity_deltas.md` (with an explicit status and any intended alias/migration notes).

Writing rule: describe the concept as `project_root` / `--project-root`; if current implementation still exposes `--root`, document it as an alias and record the delta in `docs/cli/parity_deltas.md`.

Required:

- `docs/cli/contract.md` — command inventory and shared surfaces; exit code overview; outputs and run-summary surface; policy-to-CLI mapping notes.
- `docs/cli/flag_matrix.md` — canonical matrix of “which flags apply to which commands” (including runtime-affecting classification).
- `docs/cli/parity_deltas.md` — ledger of contract ↔ implementation deltas (help snapshot vs documented contract), with status: implemented | alias | planned | deprecated.
- `docs/cli/_snapshots/` — captured CLI help outputs (non-normative) used to verify parity and prevent regression.
- `docs/cli/topics/overview.md` — mental model: resolution → plan → run; modes; transparency expectations.
- `docs/cli/topics/paths.md` — `--project-root` (formerly `--root`; alias tracked in parity), `--project-root none` (explicit project opt-out), `--base`, `^`, `--allow-absolute`, and absolute selector gating. Also documents the convenience macro `--ad-hoc` (expands to `--project-root none --no-env`) and the macro-expansion warning behavior.
- `docs/cli/topics/selectors.md` — selector usage examples; links to `docs/reference/selector_semantics.md`.
- `docs/cli/topics/follow.md` — follow modes, constraints, boundary counts; links to `docs/reference/follow_link.md`.
- `docs/cli/topics/artifacts.md` — writes, manifests/dashboards, cache/logs.
- `docs/cli/topics/manifest.md` — manifest usage and lifecycle; `--manifest` is canonical; `--save-as` and `-s` are aliases (same semantics; any implementation deltas recorded in `docs/cli/parity_deltas.md`).
- `docs/cli/topics/config.md` — config discovery/loading; pyproject parity; (directory overrides deferred; see §5.8).
- `docs/cli/topics/plugins.md` — plugins inventory and configuration surfaces (user-facing term); maps to internal “engine” terminology via ADR-0005.

Optional (add only if present in the CLI surface area):

- `docs/cli/topics/query.md`
- `docs/cli/topics/ratchet.md`

### 3.3 Internal governance, implementation notes, and roadmaps

- `docs/_internal/policy/s11r2-policy.md` — verbatim snapshot of the vCurrent policy text (single source of truth for the rewrite).
- `docs/_internal/adr/INDEX.md` — **auto-generated** ADR index (see §3.3.1): ADR#, title + subtitle (two lines), status, and mkdocs-material compatible links; newest ADRs first. Manual prose may exist outside the generated block only.
- `docs/_internal/adr/0001-*.md` — active ADR set (rewritten) using the `####-<kebab-title>.md` naming rule; each file’s H1 includes title + subtitle.
- `docs/_internal/adr/archive/` — superseded ADR text with explicit “Non-normative (archived)” headers and pointers to replacements.
- `docs/_internal/adr/COHERENCE_CHECKLIST.md` — enforcement checklist: terminology grep list, link hygiene, run-summary completeness, parity checks.
- `docs/_internal/cli/argv_normalization.md` — how CLI argv is normalized before parsing: macro expansion, macro-only dedup, warning rules, and recommended warning-code/message shapes (implementation guidance; not a user contract).
- `docs/_internal/roadmap/windows_paths.md` — non-normative design capture for Windows path support (promotable roadmap; see §1.3.1).
- `docs/_internal/roadmap/directory_overrides.md` — non-normative design capture for directory overrides/overlays (discovery boundaries, partitioning strategy, plan identity invariants, and interactions with traversal/boundaries).
- `docs/_internal/roadmap/ci_candidates.md` — non-normative candidate list of doc linting/checking recommendations (mandatory vs recommended) for later CI or local tooling; no CI implementation is in scope for this plan.

#### 3.3.1 Auto-generated internal indexes (scripts in `scripts/docs/`)

This plan requires that certain internal navigation files be auto-generated to prevent drift and reduce manual churn.

**Guardrail (hard ceiling):** scripts under `scripts/docs/` are **documentation tooling only**. They must:

- operate only on `docs/` (and, when needed, `scripts/docs/`) paths,
- avoid repo-wide scanning beyond documentation directories,
- avoid runtime coupling to the application implementation,
- keep dependencies minimal (prefer stdlib), and
- never evolve into a parallel “implementation project.”

**ADR index generation (`docs/_internal/adr/INDEX.md`):**

- Must contain a generated block delimited by HTML comments:
  - `<!-- BEGIN: AUTO-GENERATED (scripts/docs/generate_adr_index.py) -->`
  - `<!-- END: AUTO-GENERATED -->`
- The generated table must include, at minimum:
  - **ADR#** (as a markdown link to the ADR file, mkdocs-material compatible),
  - **Title** (line 1) and **Subtitle** (line 2),
  - **Status** (Accepted | Proposed | Superseded | Rejected, as appropriate).
- Ordering is newest-first (reverse sort by ADR#).
- The generator must treat ADR title/subtitle as authoritative from the ADR file’s H1 line, and must fail if any ADR is missing a subtitle.

**Shared generation utility (required):**

- Doc-generation scripts live under `scripts/docs/`.
- A shared “generated block” utility is required (example: `scripts/docs/_generated_blocks.py`) to:
  - locate begin/end markers in a target file,
  - replace only the block contents,
  - preserve all content outside the block,
  - fail loudly if markers are missing or duplicated.
- All future doc generators must use this shared utility rather than re-implementing block replacement.

#### 3.3.2 Documentation checking and linting candidates (for `ci_candidates.md`)

This plan does **not** introduce CI workflows at this stage. Instead, it requires a single informative roadmap file (`docs/_internal/roadmap/ci_candidates.md`) that captures candidates for later adoption (either via CI or local tooling).

`ci_candidates.md` must include:

- a **Mandatory** list (high-signal, low-controversy checks that protect correctness and navigability), and
- a **Recommended** list (quality improvements that may be tuned later).

Mandatory candidates (initial recommended set to record):

- **Header block enforcement** (per §3.4): every doc created/rewritten has the required header block immediately after the title; archive docs include the “Non-normative (archived)” notice and supersedence pointers.
- **Internal link integrity**: all relative links resolve; anchors are valid; no links to missing files.
- **MADR structure check for ADRs**: required sections exist and are ordered consistently (Context/Problem, Drivers, Options, Decision, Consequences, Links).
- **Ownership non-duplication check (lightweight)**: ADRs/reference docs do not define concepts outside their “Owned concepts” list; duplicates are flagged for review.
- **Policy-conditional POSIX-only normative check**: if Policy vCurrent selects POSIX-only *input* semantics, ensure Windows-path behavior and terminology do not appear in **Normative** ADR/spec/CLI contract text (except where explicitly marked Informative/roadmap). If policy selects otherwise, this check is disabled and the alternative posture must be enforced instead. (Windows-path design capture remains confined to `docs/_internal/roadmap/windows_paths.md`.)
- **Terminology guardrails**: detect unqualified “root” in prose (prefer `project_root` / `filesystem_root`), ensure `docs/_internal` is used (never `docs/internal`), and enforce “base-relative” phrasing.
- **Markdown hygiene**: no broken fences, no trailing whitespace, consistent heading increments, and stable code block formatting.
- **Mermaid block sanity**: Mermaid fences are well-formed (syntax linting is optional, but structural validity is mandatory).
- **Archive immutability guard**: prevent edits to files under `docs/_internal/adr/archive/` (policy-level check; implementation later).
- **ADR title/subtitle consistency**: `docs/_internal/adr/INDEX.md` titles/subtitles match the ADR files’ title/subtitle lines exactly.
- **Identifier centralization**: no normative doc defines ID/token computation rules outside `docs/reference/identifiers.md` (others may reference only).

Recommended candidates (record as optional/tunable):

- **Spell/wording lint** (domain dictionary + exclusions).
- **Style lint** (tone/clarity rules; e.g., Vale).
- **Consistent wrap/line-length policy** (if adopted).
- **Example validation**: JSON examples parse; TOML examples parse (where present).
- **Cross-doc parity assertions**: ensure `docs/cli/flag_matrix.md` covers all flags mentioned in topic docs; ensure parity deltas are recorded when snapshots differ.

File requirements (same rigor as other supplementary docs):

- `ci_candidates.md` must follow §3.4 header blocks and be explicitly marked **Informative**.
- It must clearly state: “Candidate recommendations only; no CI implementation is implied by inclusion.”

### 3.4 Required header blocks (all docs)

To keep the document set navigable over time, every file created or rewritten under this plan must begin with a short header block immediately after the title.

Required header contents (concise):

- **Purpose:** one paragraph describing what the document governs.
- **Status:** `Normative` (contract/spec) or `Informative` (roadmap/archive/examples).
- **Owned concepts:** 3–8 bullets naming the concepts this document owns; non-owners link out.
- **Primary links:** owners it depends on (ADR and/or reference spec), plus CLI topic links where relevant.

Header block size cap: keep the header block short (typically **6–12 lines** total). One short paragraph maximum per field; do not allow the header block to crowd out MADR sections or normative spec content.

This rule applies to ADRs, reference docs, CLI docs, and roadmaps. Archive files must additionally include a prominent “Non-normative (archived)” notice and supersedence pointers.

### 3.5 Draft logs and audit trace (required)

To preserve an auditable rewrite history without excessive overhead, this plan mandates a lightweight draft-log for every document created, rewritten, or used as a source input for auto-generated outputs.
Moves/renames count as touch events and require draft-log entries that record the **old path → new path** mapping.

Log location and mirroring rule:

- For any document at path `docs/<X>/<name>.md`, its draft log must exist at: `docs/_internal/draft_logs/<relative-path-from-docs-root>.md` (mirror the source path, rooted at `draft_logs/`).
- This includes ADRs (`docs/_internal/adr/*`), reference specs (`docs/reference/*`), CLI docs (`docs/cli/*`), internal docs/roadmaps (`docs/_internal/*`), and auto-generated outputs (e.g., `docs/_internal/adr/INDEX.md`).

Minimum logging requirements (per change):

- **Timestamp:** ISO 8601 with timezone.
- **Phase:** the plan phase being executed (Phase 0–Phase 7).
- **Document class:** ADR | Reference | CLI | Internal | Roadmap | Script | Generated output.
- **Summary:** 3–8 bullets describing what changed and why.
- **Requirements checklist:** a predefined checklist appropriate to the document class (see below), marked complete/incomplete.
- **Inputs consulted:** which source docs, snapshots, or ADRs were used.

Predefined checklists (include verbatim in each log entry for the relevant class):

- **ADR checklist (Normative decision record):**
  - MADR sections present and proportionate.
  - ADR records **decisions and delegations** only; it does **not** define exhaustive semantics, schemas, grammars, or inventories.
  - Scope boundaries enforced per ADR index (“Must not contain” items are absent).
  - **Backbone retention map (required):**
    - Retained invariants (from draft-2 and/or the immediately preceding accepted ADR).
    - Intentionally changed invariants (and why Policy vCurrent forces/permits the change).
    - Where each invariant now lives (ADR vs reference spec), with links.
  - Links updated only for the active ADR set; archived ADR links remain valid and retain the archived titles.
  - Title/subtitle/status/date/deciders correct.
- **Reference spec checklist (Normative):**
  - Owns exactly the semantics/schemas stated in the doc header; adjacent domains link out.
  - Defines required fields, types, validation rules, and stability/compatibility guarantees.
  - Uses `docs/reference/error_codes.md` for coded events (no ad-hoc code invention).
  - Cross-links to the deciding ADR(s) and relevant CLI topics.
- **CLI doc checklist (Contract):**
  - Contract aligns with reference specs; differences are recorded in `docs/cli/parity_deltas.md` with status (implemented | alias | planned | deprecated).
  - No behavior is invented; examples are consistent with specs.
  - Macro expansion and warnings are documented in a single canonical place and linked.
- **Internal/roadmap checklist (Informative):**
  - Clearly marked Informative/Non-normative.
  - Written as “promotable without refactor” where required, including explicit non-foreclosure constraints.
  - Does not introduce normative semantics or override ADR/spec content.
- **Script/generated checklist:**
  - All documentation tooling lives under `scripts/docs/`.
  - Generators are idempotent and use shared marker/delineation utilities.
  - Generated outputs contain begin/end generation markers; regeneration produces stable diffs.
  - The generator run is recorded in the generated output’s draft log.

Source-file log rule (auditing):

- Every file **touched** by the rewrite (created, rewritten, or used as a generator input) must have a corresponding draft log file at the mirrored path.
- Auto-generated documents must always have a draft log entry for each generation run. Generator runs may list source inputs in the generated file’s log; source logs are required to exist but do not need an entry unless the source file itself was modified.

---

## 4. Diagrams (Mermaid) and placement

**Rule:** The authoritative Mermaid source lives in the owning ADR or owning reference spec. Other docs may reuse excerpts only if they clearly label the origin (e.g., “From ADR-0006”) and do not modify the authoritative diagram in-place.

| Diagram | Purpose | Primary home |
| ---: | --- | --- |
| Resolution → Plan → Run pipeline | Immutability and phase boundaries | ADR-0003 |
| Sources/precedence and `--no-env` removal | Resolution order clarity | ADR-0003 |
| Run artifact collection overview | Run summary, findings, resolution log, and auxiliary artifacts | `docs/reference/run_artifacts.md` (required by ADR-0003) |
| CLI argv normalization pipeline | Macro expansion and macro-only dedup/warnings | ADR-0003 (details: `docs/_internal/cli/argv_normalization.md`) |
| Detached Project Mode decision tree | Detached disclosure + constraints | ADR-0003 |
| Path resolution pipeline (`^`, allow-absolute) | Canonical path behavior | ADR-0006 |
| Selector evaluation pipeline | Include/exclude ordering + selector rejection (fatal on scope change) | ADR-0001 |
| Follow & boundary inclusion flow | Follow modes, boundary counts, cycle detection | ADR-0008 |
| Link chain schema overview | Provenance model | ADR-0008 |
| Artifact write gating | Auto/off vs explicit outputs; detached suppression | ADR-0007 |
| Cache resolution chain | Corrected defaults + disable reasons | ADR-0007 |
| Config discovery/loading sequence | Avoid circularity | ADR-0009 |
| Engine plan dedupe flow | Engine equivalence dimensions | ADR-0002 |
| Repository layering dependency graph | Prevent cycles | ADR-0004 |

---

## 5. Ambiguity eliminations to encode (clarifications; not independent authority)

This section resolves policy-adjacent ambiguities that must be explicitly encoded in the rewritten ADRs/specs. If any existing draft contradicts these items, the draft is superseded.

**Interpretation rule:** The items below are clarifications that must be *encoded* in their canonical owner documents; this plan is not an additional policy layer. Each subsection names its owner(s).

| Subsection | Canonical owner(s) | Primary encoding home |
| --- | --- | --- |
| §5.1 Boundary terms in runs without a project | ADR-0003 + `docs/reference/run_summary.md` | ADR text + run-summary disclosure rules |
| §5.2 Follow modes in Ad-hoc vs Project Mode | ADR-0008 + `docs/reference/follow_link.md` | Follow policy + link-chain provenance schema |
| §5.3 Detached runs: identity and safe defaults | ADR-0003 + ADR-0007 + `docs/reference/defaults.md` | Identity disclosure + artifact defaulting |
| §5.4 `--no-env` is source removal | ADR-0003 + ADR-0009 + `docs/reference/config_loading.md` | Source precedence + config/env discovery |
| §5.5 Roadmap posture: Windows path support | ADR-0006 + policy snapshot + `docs/_internal/roadmap/windows_paths.md` | Contract posture + roadmap note |
| §5.6 “Stable outputs” without leaking host paths | ADR-0006 + `docs/reference/path_resolution.md` + `docs/reference/run_summary.md` | Normalization + reporting contract |
| §5.7 CLI macro expansion: generalized, reusable, and layered | ADR-0003 + `docs/_internal/cli/argv_normalization.md` + CLI contract | Boundary normalization rules |
| §5.8 Directory overrides (deferred) | ADR-0009 + roadmap note | Roadmap-only until policy activates |

### 5.1 Boundary terms in runs without a project

**Owner(s):** ADR-0003 + `docs/reference/run_summary.md`.
In **Ad-hoc Mode** (running without a project; i.e., no effective project is in use):

- The only meaningful containment boundary is `base_dir`.
- **Project-boundary metrics must be reported without guesswork.** `out_of_project` (or its successor) must be defined in `docs/reference/run_summary.md` with a justified, strongly-typed representation that distinguishes:
  - *not applicable* (no project boundary exists) vs.
  - *measured count* (a project boundary exists and crossings were counted).
- “External” (for `follow=external`) means “outside `base_dir`”.

Clarification (gating vs traversal):

- **Allow-absolute** (`--allow-absolute` / `paths.allow_absolute`) gates whether the user may provide **absolute path-like inputs** (and filesystem-root anchored selector forms like `/pattern` in Ad-hoc).
- **Follow modes** (`follow=base|project|external`) gate what the traversal may **reach** after selection (e.g., via symlinks/junctions/mount jumps), including whether boundary crossings are included.
- Example: a selected target under `base_dir` may contain a symlink that points outside `base_dir`. With `follow=base`, traversal stops at the boundary; with `follow=external`, traversal may include those external targets (subject to policy and required disclosure).
These are independent: a run may forbid absolute inputs while still encountering targets outside `base_dir` when `follow=external` is selected and links cross boundaries. In those cases, reporting remains stable by using base-relative coordinates where possible and otherwise using tokens/IDs and link-chain provenance instead of emitting raw host paths.

### 5.2 Follow modes in Ad-hoc vs Project Mode

**Owner(s):** ADR-0008 + `docs/reference/follow_link.md`.

- `follow=project` is an **error** unless Project Mode is active *and* the run is **not detached** (`base_dir ⊆ project_root`).
- `follow=base` is valid in all modes; traversal includes targets only while they remain within `base_dir`.
- `follow=external` is valid in all modes; traversal may include targets outside `base_dir` (and outside `project_root` if present), subject to policy constraints and required disclosure.

### 5.3 Detached runs: identity and safe defaults

**Owner(s):** ADR-0003 + ADR-0007 + `docs/reference/defaults.md`.
Detached runs exist to support explicit `project_root` assertion while scanning a base outside the project boundary.

Requirements to encode (ADR-0003 + ADR-0007):

- The run summary must disclose `detached=true` (or equivalent), plus the asserted `project_root` and effective `base_dir`.
- Any suppression of writes (artifacts/logs/cache) must be explicit in run summary, including “why suppressed”.
- Default posture in detached runs is safety-first: automatic writes are suppressed unless policy explicitly allows and the run discloses the override.

### 5.4 `--no-env` is source removal, not “ignore some variables”

**Owner(s):** ADR-0003 + ADR-0009 + `docs/reference/config_loading.md` + `docs/reference/env_vars.md`.
`--no-env` disables environment as a *source*.

- Resolution must record whether ENV is enabled as a source.
- If ENV is enabled: record whether ENV contributed any effective values (without echoing the values themselves).
- If ENV is explicitly disabled (`--no-env`, including via `--ad-hoc` expansion): **do not read or log environment variable values**. Only disclose that ENV was disabled and by which token.
- The run summary must expose env enablement status and, where required by policy, whether ENV contributed any effective values.
- In Ad-hoc Mode selected via `--project-root none`, ENV remains enabled unless `--no-env` is set; any ENV-driven overrides (including any implicit config selection under current rules) must be disclosed clearly in the **run summary** (see `docs/reference/run_summary.md`). Findings may be used only when the disclosure is actionable as a warning.

### 5.5 Roadmap posture: Windows path support

**Owner(s):** ADR-0006 + `docs/_internal/policy/s11r2-policy.md` + `docs/_internal/roadmap/windows_paths.md`.

- The present-tense contract remains POSIX semantics for path-like inputs across CLI/ENV/config.
- The Windows path design is preserved in `docs/_internal/roadmap/windows_paths.md` and must not leak into normative specs until explicitly promoted by policy.
- Selectors remain portable canonical syntax; `\` is literal in selectors.

### 5.6 “Stable outputs” without leaking host paths

**Owner(s):** ADR-0006 + `docs/reference/path_resolution.md` + `docs/reference/run_summary.md` + `docs/reference/identifiers.md`.

- Primary reporting and selection coordinates are always **normalized base-relative paths rendered with `/`**.
- When traversal yields targets outside base/project, outputs must prefer:
  - stable tokens/hashes (for correlation and dedupe; defined in `docs/reference/identifiers.md`), and
  - link-chain provenance (for explainability; schema in `docs/reference/follow_link.md`, identifiers in `docs/reference/identifiers.md`).
- Raw absolute host paths are emitted only when explicitly permitted by policy and disclosed in the run summary.

Clarification (input gating vs traversal reach):

- **Allow-absolute** gates whether the CLI/config may *accept* absolute path-like **inputs** (e.g., an explicit target `C:/...` or `/var/...`). If not permitted, those inputs are rejected during Resolution and recorded as such.
- **Follow modes** (ADR-0008) gate whether traversal may *reach beyond* `base_dir` / `project_root` while walking the filesystem (e.g., a symlink or junction that exits the base). This can occur even when all *inputs* were base-relative.
- These are intentionally independent: a run may forbid absolute inputs while still observing out-of-base traversal caused by links; when that happens, outputs remain stable via tokens/hashes and link-chain provenance (and raw host paths remain suppressed unless separately permitted).

Example (normative intent, not an algorithm):

- User supplies only base-relative inputs; `--allow-absolute` is not set. A followed symlink exits the base. The traversal event is recorded (boundary counts + link-chain provenance), the affected items are tokenized for stability, and the run summary clearly reports that traversal reached outside base without exposing raw host paths by default.

### 5.7 CLI macro expansion: generalized, reusable, and layered

**Owner(s):** ADR-0003 + `docs/_internal/cli/argv_normalization.md` + `docs/cli/contract.md`.
This plan standardizes a generalized “macro expansion” capability for CLI ergonomics (e.g., `--ad-hoc`).

Non-negotiables:

- Macro expansion is a **generalized operation** (macro registry → token expansion) and must be reusable to avoid duplicated “special-case flags” logic.
- Macro expansion runs as a **CLI boundary normalization step** before normal parsing/`CommandSpec` construction and before Resolution.
- The macro stage is tightly scoped: it performs **only** expansion and macro-only dedup/warnings, then hands off to the normal pipeline.
- Macro normalization must **remove macro tokens** from the argv stream after expansion. Only the expanded tokens proceed to parsing/validation.

Required behavior:

- `--ad-hoc` is a convenience macro that expands to `--project-root none --no-env`.
- Ad-hoc Mode is defined as “running without a project”; `--ad-hoc` does **not** redefine Ad-hoc Mode. It exists to provide a clean, fully-explicit starting slate by disabling ENV.
- If the user supplies `--ad-hoc` and also explicitly supplies flags the macro injects, the normalization step must:
  - **warn** (e.g., `--project-root none --ad-hoc` warns that the explicit flag is covered by `--ad-hoc`), and
  - deduplicate the redundant injected tokens (prefer user-supplied tokens; drop macro-injected duplicates).

Dedup preference rule:

- When an explicit user-supplied token duplicates a macro-injected token, keep the user-supplied token and drop the macro-injected duplicate (after emitting the warning).

Conflict handling rule:

- All substantive validation (including conflicts such as `--project-root src --ad-hoc`) happens in the normal parsing/validation pipeline **after** macro expansion and macro-only dedup.

Implementation guidance (non-normative):

- For single-valued options where last-one-wins would hide conflicts, collect occurrences (e.g., append into a list) and validate once after parsing to raise errors on distinct duplicates introduced by macro expansion or aliases.

Scope clarification:

- The macro stage may deduplicate **only** (a) duplicates it injects itself and (b) duplicates between injected tokens and already-present explicit tokens.
- The macro stage must not attempt to normalize, deduplicate, or validate other CLI tokens (aliases like `-d` vs `--dashboard`, repeated idempotent flags, or last-one-wins semantics). Those remain the responsibility of the normal parser/validator.

Note on duplicate idempotent flags:

- Duplicates for non-macro, idempotent flags (e.g., repeated `--dashboard` / `-d`) are not addressed by the macro stage. Their behavior remains governed by the normal parser/validator and the CLI contract docs.

### 5.8 Directory overrides (deferred)

**Owner(s):** ADR-0009 + `docs/_internal/roadmap/directory_overrides.md` (roadmap-only until policy activates).

- **Directory overrides are deferred:** directory-level configuration overlays (and any plan partitioning derived from them) are not specified as normative behavior in this ADR/reference set until the core contract stabilizes.
- **Forward-compatibility is mandatory:** ADR-0002 (planning) and ADR-0009 (config) must preserve an **overlay-ready plan identity** model so that overlays can be introduced later without breaking plan equivalence and dedupe semantics.
- Create an informative, promotable roadmap: `docs/_internal/roadmap/directory_overrides.md`, which must capture:
  - discovery boundaries (what constitutes an overlay, and where discovery can occur)
  - partitioning strategy (how a single scope becomes partitioned invocations)
  - plan identity dimensions and dedupe invariants (effective scope segment + effective config inputs + relevant resolution dimensions)
  - interactions with follow/boundaries (including link traversal and boundary counts)
  - conflict/precedence narratives (how overlays relate to CLI/ENV/config precedence)
- If any overlay behavior exists in current implementation, treat it as **non-normative**, document it only as a parity delta (`docs/cli/parity_deltas.md`), and do not let it shape normative ADR wording.

---

## 6. Mapping required changes (legacy ADR drafts → new homes)

This is the working map used during rewrites to remove duplication and supersede conflicts.

### 6.1 ADR-0001 include/exclude drafts → ADR-0001 + ADR-0006 + ADR-0008 + reference specs

- Move all base/project-root resolution and `^` anchor semantics to **ADR-0006** (and `docs/reference/path_resolution.md`).
- Keep ADR-0001 as a MADR decision record (no normative selector semantics). The canonical, normative selector syntax *and* evaluation semantics live in `docs/reference/selector_semantics.md` and are referenced from ADR-0001 and the CLI docs.
- Ensure `/pattern` selectors are handled per policy:
  - **Project Mode:** leading `/` anchors selector evaluation to `project_root` (project-root-anchored selectors).
  - **Ad-hoc Mode:** leading `/` denotes filesystem-root anchoring; it is ignored/rejected unless absolute gating permits (`--allow-absolute` / `paths.allow_absolute`), in which case it anchors to the filesystem root.
  - Any selector rejected due to gating (e.g., `/`-anchored forms in Ad-hoc Mode without allow-absolute) generates a selection-time **Error Finding**, is counted in the run summary, and **aborts before Planning** (no silent scope change).
- In the POSIX-only selector contract, `/` is the only separator in any path-like selector syntax; `\` is always a **literal character** in both patterns and matched paths.
- Remove any selector semantics that treat `\` as a separator.
- Selection-time findings remain valid (e.g., rejected selectors, bounded exclusions), but finding schema ownership lives in ADR-0003 / `docs/reference/findings.md`.
- Replace “discovery depth” framing with follow-mode traversal rules (ADR-0008 + `docs/reference/follow_link.md`).
- Move any output-path rules (e.g., `--manifest` / `--save-as` / `-s`, trailing `/` intent, dashboards) to ADR-0006 (path resolution) and ADR-0007 (write rules).
- `--manifest` is standard equipment and canonical for manifest paths (input/output). `--save-as` and `-s` are aliases with identical semantics. The canonical user-facing definition lives in `docs/cli/topics/manifest.md`; `docs/reference/artifacts.md` owns the normative write/format rules.

### 6.2 ADR-0003 Policy Boundaries (draft-2) → ADR-0003 constitution (expanded)

Promote ADR-0003 to the “constitution”:

- Preserve the draft-2 **Resolution Domains** structure (minimal changes): keep the sectioning and domain partitioning intact unless a change is required by Policy vCurrent.
- Retain the draft-2 **“What Policy/Planning/Execution may do”** permission lists **verbatim** unless Policy vCurrent forces edits.
- Preserve and restate the draft-2 **Runner vs Executor** role boundary (minimal changes): keep responsibilities and orchestration boundaries intact; adjust only for terminology consistency.
- mode definitions (Workspace is not a mode)
- source precedence model and `--no-env` as source removal
- CLI boundary argv normalization (macro expansion and macro-only warnings/dedup)
- detached run identity disclosure
- mandatory run summary: minimum required fields and disclosure rules
- strict pipeline immutability (Resolution → Plan → Run)

### 6.3 ADR-0005 Naming Conventions (draft-2) → ADR-0005 only (remove non-naming content)

- Remove token/path models and any cache/write defaults from ADR-0005.
- Move all enumerated default values (e.g., cache directory names/paths previously listed in draft-2) into `docs/reference/defaults.md`; ADR-0005 may link to the defaults catalog but must not restate values.
- Keep reserved suffix rules and boundary translation rules only.
- Preserve the draft-2 architectural invariant: **translations happen only at adapters/boundaries** (wire ↔ internal), never “mid-layer.” `docs/reference/naming_conventions.md` must explicitly encode boundary translation points and casing/serialization rules per boundary.
- Align naming guidance with link-chain schema field naming (ADR-0008 reference).

### 6.4 ADR-0002 Plugin/Engines (draft-2) → ADR-0002 (resolved inputs only)

- ADR-0002 must assume inputs are already resolved (per ADR-0003/0006/0009).
- ADR-0002 must explicitly encode **overlay-ready plan identity invariants** (directory overrides deferred):
  - plan identity includes the **effective scope segment(s)** being executed
  - plan identity includes the **effective config inputs** used to derive behavior (source-resolved, not raw)
  - plan identity includes any **resolution dimensions** that affect engine behavior (e.g., follow mode, allow-absolute gating), as defined by Policy vCurrent
  - dedupe/equivalence comparisons must use these dimensions so that future overlays can be introduced without changing the meaning of “same plan”
- Encode plan partitioning and per-engine plan dedupe/canonicalization for the resolved scope (overlay algorithm deferred; see §5.8 roadmap).
- Carry forward the draft-2 planning invariant verbatim: **when BOTH CURRENT and TARGET plans are requested, and they are equivalent after canonicalization, execute TARGET only** (and record the dedupe decision in planning outputs).
- Carry forward the draft-2 guardrail: **explicit empty scope** (post-resolution/post-selector evaluation) is a configuration error that produces engine deselection (hard error) rather than silently falling back to tool defaults.
- Move any CLI inventory of engines/adapters to `docs/cli/topics/plugins.md`.

### 6.5 ADR-0004 Taxonomy (draft-2) → ADR-0004 only (link hygiene)

- Keep ADR-0004 taxonomy-only; remove behavioral policies.
- Preserve the draft-2 conceptual model: repository layering (presentation → orchestration → domain) and **adapter/boundary edges as first-class concerns**. ADR-0004 remains conceptual; ADR-0005 remains mechanical.
- Ensure it links to the correct ADR owner for behavior when needed (e.g., “path rules are ADR-0006”).

---

## 7. Phased execution plan (documentation work only)

### 7.0 Cross-phase gates (apply at end of every phase)

These gates must pass before starting the next phase.

- **Policy snapshot stability:** the Phase 0 policy snapshot remains unchanged (except via an explicit policy revision + plan bump).
- **ADR index is current:** run `python scripts/docs/generate_adr_index.py` and confirm the working tree is unchanged (generated block up to date).
- **Concept-owner coherence:** complete `docs/_internal/adr/COHERENCE_CHECKLIST.md` and resolve any “one concept, one owner” collisions.
- **Link hygiene:** no broken intra-doc links within `docs/` (especially ADR → reference spec links and `INDEX.md` links).
- **Draft logs:** draft logs exist and are updated for every doc created or rewritten in the phase (per §3.5).

### 7.1 Foundational prerequisites (established in Phase 2; must remain true in Phases 3–7)

Once Phase 2 is complete, later phases must not regress these invariants:

- **ADR-0003 (constitution):** includes a clear **Decision visibility** section (what is surfaced in CLI summaries vs artifacts) and cites the Resolution Log definition in `docs/reference/run_artifacts.md`.
- **Schemas are complete contracts:** `docs/reference/run_summary.md`, `docs/reference/findings.md`, `docs/reference/engine_errors.md`, `docs/reference/run_artifacts.md`, and `docs/reference/identifiers.md` are internally consistent and define required fields/types and stability rules (no “hand-wavy” contracts).
- **Engine errors minimum surface:** `docs/reference/engine_errors.md` includes a minimum required field set and explicitly states **stderr is never diagnostics**.
- **Policy-cited carry-forward:** ADR-0003 contains (or links to) a **verbatim carry-forward checklist** and records any forced changes with a citation to the Phase 0 policy snapshot.
- **Immutability is explicit:** “Resolution → Plan → Run” immutability is defined in ADR-0003 and referenced by other ADRs (later stages must not redo discovery/precedence).
- **Mode + disclosure are stable:** mode definitions, minimum run-summary disclosure fields, and identifier/token usage are defined and linked.
- **Path posture is policy-derived and unambiguous:** ADR-0006 cites the policy snapshot for the POSIX-only contract posture; Windows input support remains explicitly **roadmap-only** under `docs/_internal/roadmap/windows_paths.md`.

---

### Phase 0 — Inventory, freeze, and governance scaffolding

**Actions:**

- Read and understand the s11r2 Rewrite Governance system by reading `docs/_internal/policy/s11r2/AGENTS.md` and linked docs.
- Confirm `docs/_internal/policy/s11r2-policy.md` exists, which will be deemed as Policy vCurrent. Ensure it includes stable section anchors suitable for citations by ADRs/specs and this plan.
  - **Stop condition:** if no canonical policy exists, do not proceed beyond Phase 0; Policy vCurrent must be authored/approved outside this plan before Phase 1 begins.
- Create `docs/_internal/adr/INDEX.md` and `docs/_internal/adr/archive/`.
- Create `scripts/docs/` and add:
  - `scripts/docs/_generated_blocks.py` (shared generated-block replacement utility),
  - `scripts/docs/generate_adr_index.py` (ADR index generator).
- Generate the ADR index block in `docs/_internal/adr/INDEX.md` (generated region only; manual prose may exist above/below markers).
- Create stubs for:
  - `docs/_internal/cli/argv_normalization.md`,
  - `docs/_internal/roadmap/windows_paths.md`,
  - `docs/_internal/roadmap/directory_overrides.md` (explicitly deferred until policy activates),
  - `docs/_internal/roadmap/ci_candidates.md` (doc-check recommendations; non-normative).
- Capture current CLI help output snapshots under `docs/cli/_snapshots/` (non-normative).

**Acceptance criteria:**

- `docs/_internal/policy/s11r2-policy.md` exists, is **verbatim** (no plan-authored mandates), and contains stable anchors for every clause cited by this plan.
- `docs/_internal/adr/INDEX.md` contains the generated-block markers and the generated ADR table is current (newest ADRs first).
- Every existing ADR draft is referenced from `INDEX.md` exactly once.
- CLI help snapshots are captured with the command invocation recorded alongside the snapshot (for reproducibility).
- Cross-phase gates in §7.0 pass.

---

### Phase 1 — Create document skeletons and link scaffolding

**Actions:**

- Read and understand the s11r2 Rewrite Governance system by reading `docs/_internal/policy/s11r2/AGENTS.md` and linked docs.
- Add stubs for ADR-0001..ADR-0009 with titles/subtitles (per §2), “must not contain” scope boundaries, and links to canonical owners.
- Create empty `docs/reference/*` and `docs/cli/*` files listed in Section 3 so cross-links can be added early.
- Create `docs/_internal/adr/COHERENCE_CHECKLIST.md` and wire it as a review gate for documentation changes.

**Acceptance criteria:**

- Every ADR stub has: H1 title, subtitle line, Status line, and the five MADR headings (even if placeholder content).
- Each stub includes explicit “must not contain” scope boundaries and at least one outbound link to its canonical reference spec owner(s).
- `docs/_internal/adr/COHERENCE_CHECKLIST.md` exists and includes checks for: concept ownership collisions, link hygiene, schema completeness markers, and “no ADR flag inventories.”
- Cross-phase gates in §7.0 pass.

---

### Phase 2 — Foundational constitution + paths (highest fan-out)

**Actions:**

- Read and understand the s11r2 Rewrite Governance system by reading `docs/_internal/policy/s11r2/AGENTS.md` and linked docs.
- Rewrite ADR-0003 (constitution) to final MADR form, including required diagrams.
- Preserve ADR-0003 draft-2 structure with minimal changes: keep Resolution Domains partitioning and the Runner vs Executor role boundary intact.
- Rewrite ADR-0006 (paths) to final MADR form; create `docs/reference/path_resolution.md`.
- Create `docs/reference/run_summary.md` and `docs/reference/findings.md` (minimum viable but complete schemas; see §3 definition).
- Create baseline `docs/reference/error_codes.md` (stable, documented codes referenced by Findings and fatal-gate behavior).
- Create baseline `docs/reference/engine_errors.md` (schema and minimum required field set; **stderr is never diagnostics**).
- Create baseline `docs/reference/identifiers.md` (minimum required IDs/tokens referenced by run summary/findings/follow specs).
- Create baseline `docs/reference/run_artifacts.md` (formal artifact collection, including the Resolution Log).

**Acceptance criteria:**

- ADR-0003 is final MADR form and includes: Resolution Domains, Runner vs Executor boundary, Decision visibility section, and explicit Resolution → Plan → Run immutability.
- ADR-0006 is final MADR form and cites the policy snapshot for path contract posture and allow-absolute gating; any Windows-path discussion is confined to `docs/_internal/roadmap/windows_paths.md`.
- `docs/reference/run_summary.md` and `docs/reference/findings.md` meet the “minimum viable but complete schema” definition (required surface complete; optional fields explicitly marked).
- `docs/reference/engine_errors.md` states **stderr is never diagnostics** and defines the minimum field set (including engine identity, command, exit status, and captured stdio metadata).
- `docs/reference/run_artifacts.md` defines the required artifact set and contains the Resolution Log schema referenced by ADR-0003.
- The terminology set is consistent across ADR-0003/0006 and reference docs (`project_root`, `base_dir`, “base-relative”).
- Cross-phase gates in §7.0 pass.

---

### Phase 3 — Config loading parity

**Actions:**

- Read and understand the s11r2 Rewrite Governance system by reading `docs/_internal/policy/s11r2/AGENTS.md` and linked docs.
- Rewrite ADR-0009 to define core config discovery/loading and `pyproject.toml` parity rules (no directory-config recursion or partitioning behavior in this pass).
- Create `docs/reference/config_loading.md` and `docs/reference/env_vars.md`.
- Update `docs/cli/topics/config.md` and `docs/cli/contract.md` with authoritative mapping rules.

**Acceptance criteria:**

- ADR-0009 is final MADR form and is explicitly scoped to discovery/loading + precedence + parity; directory overrides remain deferred and are referenced only via roadmap note.
- `docs/reference/config_loading.md` defines discovery order, precedence resolution, and the exact `pyproject.toml` parity rules; it does not introduce behavior not cited to policy snapshot.
- `docs/reference/env_vars.md` enumerates the env-var contract and documents `--no-env` as a source removal (not partial ignoring).
- CLI config docs reflect the same precedence and parity rules (no contradictory prose).
- Foundational prerequisites in §7.1 remain satisfied.
- Cross-phase gates in §7.0 pass.

---

### Phase 4 — Selectors + follow/provenance

**Actions:**

- Read and understand the s11r2 Rewrite Governance system by reading `docs/_internal/policy/s11r2/AGENTS.md` and linked docs.
- Rewrite ADR-0001 to final MADR form; create `docs/reference/selector_semantics.md`.
- During ADR-0001 rewrite, remove any statement implying symlinks are not supported; align with follow/symlink policy (ADR-0008 + `docs/reference/follow_link.md`).
- Rewrite ADR-0008 to final MADR form; create `docs/reference/follow_link.md`.
- Update CLI topics: `selectors.md` and `follow.md`.

**Acceptance criteria:**

- ADR-0001 is final MADR form and delegates exhaustive grammar/algorithms to `docs/reference/selector_semantics.md`.
- ADR-0008 is final MADR form and delegates exhaustive traversal constraints/provenance schema to `docs/reference/follow_link.md` (including cycle detection and boundary counting).
- `docs/reference/selector_semantics.md` and `docs/reference/follow_link.md` define complete, mechanically actionable rules and are consistent with ADR-0003/0006 terminology and identifiers.
- No doc states (or implies) that symlinks are unsupported if follow modes are supported; the posture is unambiguous.
- Foundational prerequisites in §7.1 remain satisfied.
- Cross-phase gates in §7.0 pass.

---

### Phase 5 — Artifacts, writes, cache, and logs

**Actions:**

- Read and understand the s11r2 Rewrite Governance system by reading `docs/_internal/policy/s11r2/AGENTS.md` and linked docs.
- Rewrite ADR-0007 to final MADR form.
- Create `docs/reference/artifacts.md`, `docs/reference/defaults.md`, `docs/reference/cache.md`, and `docs/reference/logs.md`.
- Update CLI topic `artifacts.md`.

**Acceptance criteria:**

- ADR-0007 is final MADR form and delegates exhaustive behavior to the reference docs (no embedded default tables).
- `docs/reference/defaults.md` is the single canonical home for default names/paths; ADRs link but do not restate defaults.
- `docs/reference/artifacts.md` defines write gating, required artifacts, and disclosure rules consistent with ADR-0003 Decision visibility.
- `docs/reference/cache.md` and `docs/reference/logs.md` define enablement/disablement and required disclosure fields (including reasons for disablement).
- Foundational prerequisites in §7.1 remain satisfied.
- Cross-phase gates in §7.0 pass.

---

### Phase 6 — Engine planning, repo taxonomy, naming + CLI contract completion

**Actions:**

- Read and understand the s11r2 Rewrite Governance system by reading `docs/_internal/policy/s11r2/AGENTS.md` and linked docs.
- Rewrite ADR-0002, ADR-0004, ADR-0005 to final MADR form.
- Create `docs/reference/engine_planning.md` (normative plan equivalence/canonicalization tables and examples; referenced by ADR-0002).
- Create `docs/reference/taxonomy.md` (canonical glossary + repository layering model; referenced by ADR-0004).
- Create `docs/reference/naming_conventions.md` (exhaustive naming rules + boundary translation rules; referenced by ADR-0005).
- Complete `docs/cli/flag_matrix.md` and `docs/cli/contract.md` using CLI snapshots as a verification aid (snapshots remain non-normative).
- Ensure every user-facing behavior described in prose has an inventory home (flag matrix, topic docs, contract doc).

**Acceptance criteria:**

- ADR-0002/0004/0005 are final MADR form and respect scope boundaries (ADR-0004 conceptual taxonomy only; ADR-0005 mechanical naming/translation only).
- `docs/reference/engine_planning.md` includes: plan identity invariants, canonicalization/equivalence rules, the draft-2 **CURRENT/TARGET dedupe rule (TARGET canonical)**, and the **explicit empty scope = hard error** guardrail.
- `docs/reference/taxonomy.md` preserves the layering model (presentation → orchestration → domain) and explicitly treats adapter/boundary edges as first-class concerns.
- `docs/reference/naming_conventions.md` encodes boundary-only translation points and casing/serialization rules per boundary, including reserved suffix contracts.
- CLI contract and flag matrix cover the full observed CLI surface; any intentionally non-normative flags are explicitly labeled and justified in docs/_internal notes (not silently omitted).
- Foundational prerequisites in §7.1 remain satisfied.
- Cross-phase gates in §7.0 pass.

---

### Phase 7 — Archive superseded ADR text and remove dependencies

**Actions:**

- Read and understand the s11r2 Rewrite Governance system by reading `docs/_internal/policy/s11r2/AGENTS.md` and linked docs.
- Move old ADR content to `docs/_internal/adr/archive/` with “Non-normative (archived)” headers and supersedence pointers.
- Before archiving legacy ADR drafts, correct any premature Status values to match reality (Rejected/Superseded), then treat the archived file as immutable.
- After a document is archived, **do not modify it** (including titles). Fix references and add notes outside the archive instead.
- Update all internal links to point only to rewritten ADRs and current reference docs.

**Acceptance criteria:**

- Normative docs do not depend on archived ADRs for normative behavior (archived ADRs may be linked for history only).
- Every archived draft-2 ADR has its Status corrected (if needed) and includes a supersedence pointer to its replacement(s); the ADR index records the chain.
- No archived document is edited after being placed under `docs/_internal/adr/archive/` (immutability enforced by review).
- All internal links point to current ADRs/specs; archived links (if any) are explicitly labeled as historical.
- Cross-phase gates in §7.0 pass.

## 8. Rewrite checklists (gates)

### 8.1 MADR compliance checklist (per ADR)

- Context/Problem: only why the decision exists (no hidden policy).
- Drivers: explicit bullet list.
- Options: at least 2 with accept/reject reasoning.
- Decision: concise and normative; links out for exhaustive detail.
- Consequences: concrete operational pros/cons.
- Links: only to current ADRs and reference specs; no stale dependencies.

### 8.2 “No scope creep” checklist

- No flag inventories inside ADRs.
- No full grammars inside ADRs (belongs to `docs/reference/*`).
- No duplicated definitions across ADRs (enforce via ownership matrix).
- Defaults live with the correct owner:
  - base/path/portable syntax: ADR-0006
  - selector evaluation: ADR-0001
  - link traversal/provenance: ADR-0008
  - cache/artifacts/logs: ADR-0007
  - config loading/parity: ADR-0009

### 8.3 Terminology checklist (repo-wide)

- User-facing docs use “plugin”; internal architecture and ADR-0002 use “engine”. ADR-0005 defines the translation boundary and naming rules.
- `project_root` and `base_dir` used consistently; avoid “root” unqualified in prose (use `project_root` or `filesystem_root` as appropriate).
- “Base-relative” replaces “project-root-relative” everywhere.
- `include` / `exclude` are canonical terms (singular); resolved collections are lists.
- `*Policy/*Resolver/*Resolution/*Plan/*Executor` used per ADR-0005 naming contract.

---

## Appendix A — Known supersedences to enforce

- Any draft text that treats `.cache/` (or other legacy values) as the canonical cache default is superseded by Section 1.3.2 and the defaults catalog (`docs/reference/defaults.md`).
- Any plan/draft that makes `<project_root>` the *primary* Project Mode cache default (instead of `<tool_home>`) is superseded by Section 1.3.2.
- Any selector semantics that treat `\` as a path separator are superseded (selectors are portable).
- Any document that invents a second “home” for path resolution, link traversal semantics, cache defaults, or config precedence must be rewritten to link to the canonical owner.
