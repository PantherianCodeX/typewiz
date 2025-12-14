# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""High-level audit orchestration entry points."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ratchetr.audit.execution import (
    build_engine_plan,
    execute_engine_mode,
    resolve_engine_options,
    resolve_scope_for_mode,
)
from ratchetr.audit.options import merge_audit_configs
from ratchetr.audit.paths import normalise_paths
from ratchetr.cache import EngineCache
from ratchetr.config import AuditConfig, Config, load_config
from ratchetr.core.model_types import LogComponent, Mode, SeverityLevel
from ratchetr.core.types import RunResult
from ratchetr.dashboard import build_summary
from ratchetr.engines import EngineContext, resolve_engines
from ratchetr.exceptions import ConfigError
from ratchetr.logging import structured_extra
from ratchetr.manifest.builder import ManifestBuilder
from ratchetr.runtime import detect_tool_versions

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ratchetr.core.summary_types import SummaryData
    from ratchetr.core.type_aliases import RelPath
    from ratchetr.engines.base import BaseEngine, EnginePlan
    from ratchetr.manifest.typed import ManifestData

logger: logging.Logger = logging.getLogger("ratchetr.audit")


@dataclass(slots=True)
class AuditResult:
    """Structured result payload returned by :func:`run_audit`."""

    manifest: ManifestData
    runs: list[RunResult]
    summary: SummaryData | None = None
    error_count: int = 0
    warning_count: int = 0


@dataclass(slots=True)
class _AuditInputs:
    root: Path
    audit_config: AuditConfig
    include_paths_normalised: list[RelPath]
    cli_paths: list[str] | None
    engines: list[BaseEngine]
    tool_versions: dict[str, str]
    cache: EngineCache


def _determine_include_paths(
    root: Path,
    audit_config: AuditConfig,
    include_paths: Sequence[str] | None,
) -> list[RelPath]:
    """Determine default paths for audit with contract-defined fallback.

    Precedence:
    1. Explicit include_paths argument (highest priority)
    2. Config audit.include_paths
    3. Default: ["."] (scan everything from root, per contract)

    Args:
        root: Project root directory.
        audit_config: Audit configuration.
        include_paths: Explicit paths override.

    Returns:
        Normalized relative paths to audit.
    """
    # Contract-defined default: scan everything from root
    raw_include_paths = list(include_paths) if include_paths else (audit_config.include_paths or ["."])
    return normalise_paths(root, raw_include_paths)


def _prepare_audit_inputs(
    *,
    project_root: Path,
    config: Config | None,
    override: AuditConfig | None,
    include_paths: Sequence[str] | None,
) -> tuple[Config, _AuditInputs]:
    cfg = config or load_config(None)
    audit_config = merge_audit_configs(cfg.audit, override)
    root = project_root
    include_paths_normalised = _determine_include_paths(root, audit_config, include_paths)
    engines = resolve_engines(audit_config.runners)
    tool_versions = detect_tool_versions([engine.name for engine in engines])
    cache = EngineCache(root)
    inputs = _AuditInputs(
        root=root,
        audit_config=audit_config,
        include_paths_normalised=include_paths_normalised,
        cli_paths=None,  # CLI threading deferred to orchestration refactor
        engines=engines,
        tool_versions=tool_versions,
        cache=cache,
    )

    logger.debug(
        "Audit inputs resolved root=%s include_paths=%s runners=%s tool_versions=%s",
        root,
        [str(path) for path in include_paths_normalised],
        [engine.name for engine in engines],
        tool_versions,
        extra=structured_extra(
            component=LogComponent.CLI,
            details={"runners": len(engines), "root_source": "cli_context"},
        ),
    )
    return cfg, inputs


def _iterate_modes(audit_config: AuditConfig) -> list[Mode]:
    modes: list[Mode] = []
    if not audit_config.skip_current:
        modes.append(Mode.CURRENT)
    if not audit_config.skip_target:
        modes.append(Mode.TARGET)
    return modes


# ignore JUSTIFIED: Per-engine deduplication requires branching logic that cannot be
# meaningfully extracted without obscuring the critical equivalence-checking flow.
# try-except in loop is unavoidable for per-mode scope resolution error handling.
def _run_engines(inputs: _AuditInputs) -> tuple[list[RunResult], bool]:  # noqa: PLR0912, C901
    """Execute engines with per-engine deduplication.

    Per-engine deduplication logic (ADR-0002):
    - Build EnginePlan for CURRENT and TARGET modes per engine
    - If plans are equivalent → run TARGET only (canonical)
    - Otherwise → run both CURRENT and TARGET

    Args:
        inputs: Audit inputs with config, paths, and engines.

    Returns:
        Tuple of (run_results, fingerprint_truncated_any).
    """
    runs: list[RunResult] = []
    truncated_any = False
    modes = _iterate_modes(inputs.audit_config)

    # Early return if no modes selected
    if not modes:
        inputs.cache.save()
        return runs, truncated_any

    # Determine if we should attempt deduplication
    should_deduplicate = Mode.CURRENT in modes and Mode.TARGET in modes

    for engine in inputs.engines:
        engine_options = resolve_engine_options(inputs.root, inputs.audit_config, engine)

        if should_deduplicate:
            # Build plans for both modes to check equivalence
            plans: dict[Mode, EnginePlan | None] = {}

            for mode in (Mode.CURRENT, Mode.TARGET):
                try:
                    # Resolve scope for this mode
                    scope = resolve_scope_for_mode(
                        mode=mode,
                        project_root=inputs.root,
                        cli_paths=inputs.cli_paths,
                        env_paths=None,  # Environment override support deferred
                        config_paths=inputs.audit_config.include_paths,
                        engine_include=engine_options.include,
                        engine_exclude=engine_options.exclude,
                    )
                    plans[mode] = build_engine_plan(
                        # ignore JUSTIFIED: BaseEngine.name is str at runtime but
                        # build_engine_plan expects ToolName type narrowing unnecessary
                        engine_name=engine.name,  # type: ignore[arg-type]
                        mode=mode,
                        project_root=inputs.root,
                        resolved_scope=scope,
                        engine_options=engine_options,
                    )
                # ignore JUSTIFIED: Per-mode error handling requires try-except in loop;
                # cannot be refactored without losing mode-specific error context
                except ConfigError as exc:  # noqa: PERF203
                    # Empty scope → configuration error (engine deselected)
                    logger.warning(
                        "Engine %s deselected for %s: %s",
                        engine.name,
                        mode,
                        exc,
                        extra=structured_extra(component=LogComponent.ENGINE, tool=engine.name, mode=mode),
                    )
                    plans[mode] = None
                    # Create config error result
                    run_result = RunResult(
                        # ignore JUSTIFIED: BaseEngine.name is str at runtime but RunResult.tool
                        # expects ToolName; type narrowing at this error path adds no value
                        tool=engine.name,  # type: ignore[arg-type]
                        mode=mode,
                        command=[],
                        exit_code=0,
                        duration_ms=0.0,
                        diagnostics=[],
                        cached=False,
                        engine_error={
                            "kind": "engine-config-error",
                            "message": str(exc),
                            "exitCode": 0,
                        },
                    )
                    runs.append(run_result)

            # Determine which modes to run based on plan equivalence
            modes_to_run: list[Mode] = []
            plan_current = plans.get(Mode.CURRENT)
            plan_target = plans.get(Mode.TARGET)

            if plan_current and plan_target:
                if plan_current.is_equivalent_to(plan_target):
                    # Plans equivalent → run TARGET only (canonical)
                    modes_to_run = [Mode.TARGET]
                    logger.info(
                        "Engine %s: plans equivalent, running TARGET only",
                        engine.name,
                        extra=structured_extra(component=LogComponent.ENGINE, tool=engine.name),
                    )
                else:
                    # Plans differ → run both
                    modes_to_run = [Mode.CURRENT, Mode.TARGET]
                    logger.debug(
                        "Engine %s: plans differ, running both modes",
                        engine.name,
                        extra=structured_extra(component=LogComponent.ENGINE, tool=engine.name),
                    )
            else:
                # One or both plans failed → run whichever succeeded
                modes_to_run = [m for m in (Mode.CURRENT, Mode.TARGET) if plans.get(m)]

        else:
            # No deduplication: run requested modes
            modes_to_run = modes

        # Execute selected modes
        for mode in modes_to_run:
            context = EngineContext(
                project_root=inputs.root,
                audit_config=inputs.audit_config,
                mode=mode,
                engine_options=engine_options,
            )
            run_result, truncated = execute_engine_mode(
                engine=engine,
                mode=mode,
                context=context,
                audit_config=inputs.audit_config,
                cache=inputs.cache,
                tool_versions=inputs.tool_versions,
                root=inputs.root,
                include_paths_normalised=inputs.include_paths_normalised,
            )
            runs.append(run_result)
            if truncated:
                truncated_any = True

    if truncated_any:
        logger.warning(
            "Fingerprint truncated across one or more runs",
            extra=structured_extra(component=LogComponent.CACHE, fingerprint_truncated=True),
        )
    else:
        logger.debug(
            "Fingerprint scan completed without truncation",
            extra=structured_extra(component=LogComponent.CACHE, fingerprint_truncated=False),
        )
    inputs.cache.save()
    return runs, truncated_any


def _build_manifest_and_summary(
    *,
    inputs: _AuditInputs,
    runs: list[RunResult],
    fingerprint_truncated: bool,
    build_summary_output: bool,
) -> tuple[ManifestData, SummaryData | None]:
    """Build manifest and summary data from engine runs.

    Does NOT write any files (manifest or dashboard).
    Returns data structures that can be persisted by the service layer.

    Args:
        inputs: Audit inputs with config and paths.
        runs: Results from engine execution.
        fingerprint_truncated: Whether fingerprint was truncated.
        build_summary_output: Whether to build summary data.

    Returns:
        Tuple of (manifest_data, summary_data_or_none).
    """
    builder = ManifestBuilder(inputs.root)
    builder.fingerprint_truncated = fingerprint_truncated
    depth = inputs.audit_config.max_depth or 3
    for run in runs:
        builder.add_run(run, max_depth=depth)
    manifest = builder.data

    summary = build_summary(manifest) if build_summary_output else None
    return manifest, summary


def _compute_run_totals(runs: list[RunResult]) -> tuple[int, int]:
    error_count = sum(run.severity_counts().get(SeverityLevel.ERROR, 0) for run in runs)
    warning_count = sum(run.severity_counts().get(SeverityLevel.WARNING, 0) for run in runs)
    return error_count, warning_count


def run_audit(
    *,
    project_root: Path,
    config: Config | None = None,
    override: AuditConfig | None = None,
    include_paths: Sequence[str] | None = None,
    build_summary_output: bool = False,
) -> AuditResult:
    """Run configured engines and collate diagnostics.

    Does NOT write any files (manifest or dashboard). Returns data structures
    that can be persisted by the service layer.

    Args:
        project_root: Repository root directory. Must be provided; root discovery
            happens at the CLI layer via resolve_paths().
        config: Resolved `ratchetr.config.Config` object. `None` triggers a
            fresh load from disk based on ``project_root``.
        override: In-memory overrides applied on top of the config file.
        include_paths: Explicit include list overriding ``config.include_paths``.
        build_summary_output: Whether to produce dashboard payloads.

    Returns:
        `AuditResult` containing the final manifest, per-engine run metadata,
        summary payloads, and aggregated severity counts.
    """
    _cfg, inputs = _prepare_audit_inputs(
        project_root=project_root,
        config=config,
        override=override,
        include_paths=include_paths,
    )
    runs, fingerprint_truncated_any = _run_engines(inputs)
    manifest, summary = _build_manifest_and_summary(
        inputs=inputs,
        runs=runs,
        fingerprint_truncated=fingerprint_truncated_any,
        build_summary_output=build_summary_output,
    )
    error_count, warning_count = _compute_run_totals(runs)
    logger.info(
        "Audit complete: %s runs (%s errors, %s warnings)",
        len(runs),
        error_count,
        warning_count,
        extra=structured_extra(
            component=LogComponent.CLI,
            counts={
                SeverityLevel.ERROR: error_count,
                SeverityLevel.WARNING: warning_count,
            },
            fingerprint_truncated=fingerprint_truncated_any,
            details={"runs": len(runs)},
        ),
    )

    return AuditResult(
        manifest=manifest,
        runs=runs,
        summary=summary,
        error_count=error_count,
        warning_count=warning_count,
    )
