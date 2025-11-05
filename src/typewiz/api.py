from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .audit_config_utils import merge_audit_configs
from .audit_execution import execute_engine_mode, resolve_engine_options
from .audit_paths import normalise_paths
from .cache import EngineCache
from .config import AuditConfig, Config, load_config
from .dashboard import build_summary, render_markdown
from .engines import EngineContext, resolve_engines
from .engines.base import BaseEngine
from .html_report import render_html
from .manifest import ManifestBuilder
from .utils import default_full_paths, detect_tool_versions, resolve_project_root

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from .summary_types import SummaryData
    from .typed_manifest import ManifestData
    from .types import RunResult

logger = logging.getLogger("typewiz")


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
    full_paths_normalised: list[str]
    engines: list[BaseEngine]
    tool_versions: dict[str, str]
    cache: EngineCache


def _determine_full_paths(
    root: Path, audit_config: AuditConfig, full_paths: Sequence[str] | None
) -> list[str]:
    raw_full_paths = (
        list(full_paths) if full_paths else (audit_config.full_paths or default_full_paths(root))
    )
    if not raw_full_paths:
        message = "No directories to scan; configure 'full_paths' or pass 'full_paths' argument"
        raise ValueError(message)
    return normalise_paths(root, raw_full_paths)


def _prepare_audit_inputs(
    *,
    project_root: Path | None,
    config: Config | None,
    override: AuditConfig | None,
    full_paths: Sequence[str] | None,
) -> tuple[Config, _AuditInputs]:
    cfg = config or load_config(None)
    audit_config = merge_audit_configs(cfg.audit, override)
    root = resolve_project_root(project_root)
    full_paths_normalised = _determine_full_paths(root, audit_config, full_paths)
    engines = resolve_engines(audit_config.runners)
    tool_versions = detect_tool_versions([engine.name for engine in engines])
    cache = EngineCache(root)
    return cfg, _AuditInputs(
        root=root,
        audit_config=audit_config,
        full_paths_normalised=full_paths_normalised,
        engines=engines,
        tool_versions=tool_versions,
        cache=cache,
    )


def _iterate_modes(audit_config: AuditConfig) -> list[Literal["current", "full"]]:
    modes: list[Literal["current", "full"]] = []
    if not audit_config.skip_current:
        modes.append("current")
    if not audit_config.skip_full:
        modes.append("full")
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
    inputs.cache.save()
    return runs, truncated_any


def _persist_manifest_and_dashboards(
    *,
    inputs: _AuditInputs,
    runs: list[RunResult],
    fingerprint_truncated: bool,
    write_manifest_to: Path | None,
    build_summary_output: bool,
) -> tuple[ManifestData, SummaryData | None]:
    builder = ManifestBuilder(inputs.root)
    builder.fingerprint_truncated = fingerprint_truncated
    depth = inputs.audit_config.max_depth or 3
    for run in runs:
        builder.add_run(run, max_depth=depth)
    manifest = builder.data

    manifest_target = write_manifest_to or inputs.audit_config.manifest_path
    if manifest_target is not None:
        out = manifest_target if manifest_target.is_absolute() else (inputs.root / manifest_target)
        builder.write(out)

    should_build_summary = (
        build_summary_output
        or inputs.audit_config.dashboard_json
        or inputs.audit_config.dashboard_markdown
        or inputs.audit_config.dashboard_html
    )
    summary = build_summary(manifest) if should_build_summary else None

    if summary is not None:
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
        target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if audit_config.dashboard_markdown:
        target = (
            audit_config.dashboard_markdown
            if audit_config.dashboard_markdown.is_absolute()
            else (root / audit_config.dashboard_markdown)
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_markdown(summary), encoding="utf-8")
    if audit_config.dashboard_html:
        target = (
            audit_config.dashboard_html
            if audit_config.dashboard_html.is_absolute()
            else (root / audit_config.dashboard_html)
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_html(summary), encoding="utf-8")


def _compute_run_totals(runs: list[RunResult]) -> tuple[int, int]:
    error_count = sum(run.severity_counts().get("error", 0) for run in runs)
    warning_count = sum(run.severity_counts().get("warning", 0) for run in runs)
    return error_count, warning_count


def run_audit(
    *,
    project_root: Path | None = None,
    config: Config | None = None,
    override: AuditConfig | None = None,
    full_paths: Sequence[str] | None = None,
    write_manifest_to: Path | None = None,
    build_summary_output: bool = False,
) -> AuditResult:
    """Run configured engines, persist artefacts, and collate diagnostics."""
    _cfg, inputs = _prepare_audit_inputs(
        project_root=project_root,
        config=config,
        override=override,
        full_paths=full_paths,
    )
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
    )
    error_count, warning_count = _compute_run_totals(runs)

    return AuditResult(
        manifest=manifest,
        runs=runs,
        summary=summary,
        error_count=error_count,
        warning_count=warning_count,
    )
