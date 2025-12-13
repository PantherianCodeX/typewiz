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

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ratchetr.audit.execution import execute_engine_mode, resolve_engine_options
from ratchetr.audit.options import merge_audit_configs
from ratchetr.audit.paths import normalise_paths
from ratchetr.cache import EngineCache
from ratchetr.config import AuditConfig, Config, load_config
from ratchetr.core.model_types import LogComponent, Mode, SeverityLevel
from ratchetr.dashboard import build_summary, render_html, render_markdown
from ratchetr.engines import EngineContext, resolve_engines
from ratchetr.json import normalise_enums_for_json
from ratchetr.logging import structured_extra
from ratchetr.manifest.builder import ManifestBuilder
from ratchetr.runtime import consume, default_full_paths, detect_tool_versions

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ratchetr.core.summary_types import SummaryData
    from ratchetr.core.type_aliases import RelPath
    from ratchetr.core.types import RunResult
    from ratchetr.engines.base import BaseEngine
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
    full_paths_normalised: list[RelPath]
    engines: list[BaseEngine]
    tool_versions: dict[str, str]
    cache: EngineCache


def _determine_full_paths(
    root: Path,
    audit_config: AuditConfig,
    full_paths: Sequence[str] | None,
) -> list[RelPath]:
    raw_full_paths = list(full_paths) if full_paths else (audit_config.full_paths or default_full_paths(root))
    if not raw_full_paths:
        message = "No directories to scan; configure 'full_paths' or pass 'full_paths' argument"
        raise ValueError(message)
    return normalise_paths(root, raw_full_paths)


def _prepare_audit_inputs(
    *,
    project_root: Path,
    config: Config | None,
    override: AuditConfig | None,
    full_paths: Sequence[str] | None,
) -> tuple[Config, _AuditInputs]:
    cfg = config or load_config(None)
    audit_config = merge_audit_configs(cfg.audit, override)
    root = project_root
    full_paths_normalised = _determine_full_paths(root, audit_config, full_paths)
    engines = resolve_engines(audit_config.runners)
    tool_versions = detect_tool_versions([engine.name for engine in engines])
    cache = EngineCache(root)
    inputs = _AuditInputs(
        root=root,
        audit_config=audit_config,
        full_paths_normalised=full_paths_normalised,
        engines=engines,
        tool_versions=tool_versions,
        cache=cache,
    )

    logger.debug(
        "Audit inputs resolved root=%s full_paths=%s runners=%s tool_versions=%s",
        root,
        [str(path) for path in full_paths_normalised],
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
    if not audit_config.skip_full:
        modes.append(Mode.FULL)
    return modes


def _run_engines(inputs: _AuditInputs) -> tuple[list[RunResult], bool]:
    runs: list[RunResult] = []
    truncated_any = False
    modes = _iterate_modes(inputs.audit_config)
    for engine in inputs.engines:
        engine_options = resolve_engine_options(inputs.root, inputs.audit_config, engine)
        for mode in modes:
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
                full_paths_normalised=inputs.full_paths_normalised,
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


def _persist_manifest_and_dashboards(
    *,
    inputs: _AuditInputs,
    runs: list[RunResult],
    fingerprint_truncated: bool,
    write_manifest_to: Path | None,
    build_summary_output: bool,
    persist_outputs: bool,
) -> tuple[ManifestData, SummaryData | None]:
    builder = ManifestBuilder(inputs.root)
    builder.fingerprint_truncated = fingerprint_truncated
    depth = inputs.audit_config.max_depth or 3
    for run in runs:
        builder.add_run(run, max_depth=depth)
    manifest = builder.data

    manifest_target = write_manifest_to or inputs.audit_config.manifest_path
    if persist_outputs and manifest_target is not None:
        out = manifest_target if manifest_target.is_absolute() else (inputs.root / manifest_target)
        builder.write(out)

    should_build_summary = build_summary_output or (
        persist_outputs
        and (
            inputs.audit_config.dashboard_json
            or inputs.audit_config.dashboard_markdown
            or inputs.audit_config.dashboard_html
        )
    )
    summary = build_summary(manifest) if should_build_summary else None

    if summary is not None and persist_outputs:
        _write_dashboard_files(inputs, summary)

    return manifest, summary if build_summary_output else None


def _write_dashboard_files(inputs: _AuditInputs, summary: SummaryData) -> None:
    audit_config = inputs.audit_config
    root = inputs.root
    if audit_config.dashboard_json:
        target = (
            audit_config.dashboard_json
            if audit_config.dashboard_json.is_absolute()
            else (root / audit_config.dashboard_json)
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = normalise_enums_for_json(summary)
        consume(target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8"))
        logger.info(
            "Wrote dashboard JSON to %s",
            target,
            extra=structured_extra(component=LogComponent.DASHBOARD, path=target),
        )
    if audit_config.dashboard_markdown:
        target = (
            audit_config.dashboard_markdown
            if audit_config.dashboard_markdown.is_absolute()
            else (root / audit_config.dashboard_markdown)
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        consume(target.write_text(render_markdown(summary), encoding="utf-8"))
        logger.info(
            "Wrote dashboard Markdown to %s",
            target,
            extra=structured_extra(component=LogComponent.DASHBOARD, path=target),
        )
    if audit_config.dashboard_html:
        target = (
            audit_config.dashboard_html
            if audit_config.dashboard_html.is_absolute()
            else (root / audit_config.dashboard_html)
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        consume(target.write_text(render_html(summary), encoding="utf-8"))
        logger.info(
            "Wrote dashboard HTML to %s",
            target,
            extra=structured_extra(component=LogComponent.DASHBOARD, path=target),
        )


def _compute_run_totals(runs: list[RunResult]) -> tuple[int, int]:
    error_count = sum(run.severity_counts().get(SeverityLevel.ERROR, 0) for run in runs)
    warning_count = sum(run.severity_counts().get(SeverityLevel.WARNING, 0) for run in runs)
    return error_count, warning_count


def run_audit(
    *,
    project_root: Path,
    config: Config | None = None,
    override: AuditConfig | None = None,
    full_paths: Sequence[str] | None = None,
    write_manifest_to: Path | None = None,
    build_summary_output: bool = False,
    persist_outputs: bool = True,
) -> AuditResult:
    """Run configured engines, persist artefacts, and collate diagnostics.

    Args:
        project_root: Repository root directory. Must be provided; root discovery
            happens at the CLI layer via resolve_paths().
        config: Resolved `ratchetr.config.Config`object. `None`triggers a
            fresh load from disk based on ``project_root``.
        override: In-memory overrides applied on top of the config file.
        full_paths: Explicit include list overriding ``config.full_paths``.
        write_manifest_to: Optional override for the manifest destination.
        build_summary_output: Whether to produce dashboard payloads.
        persist_outputs: Whether manifest/summary artefacts should be written.

    Returns:
        `AuditResult`containing the final manifest, per-engine run metadata,
        summary payloads, and aggregated severity counts.
    """
    _cfg, inputs = _prepare_audit_inputs(
        project_root=project_root,
        config=config,
        override=override,
        full_paths=full_paths,
    )
    runs, fingerprint_truncated_any = _run_engines(inputs)
    manifest, summary = _persist_manifest_and_dashboards(
        inputs=inputs,
        runs=runs,
        fingerprint_truncated=fingerprint_truncated_any,
        write_manifest_to=write_manifest_to,
        build_summary_output=build_summary_output,
        persist_outputs=persist_outputs,
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
