from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .audit_config_utils import merge_audit_configs
from .audit_execution import execute_engine_mode, resolve_engine_options
from .audit_paths import normalise_paths
from .cache import EngineCache
from .config import AuditConfig, Config, load_config
from .dashboard import build_summary, render_markdown
from .engines import EngineContext, resolve_engines
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
    cfg = config or load_config(None)
    audit_config = merge_audit_configs(cfg.audit, override)

    root = resolve_project_root(project_root)
    raw_full_paths = (
        list(full_paths) if full_paths else (audit_config.full_paths or default_full_paths(root))
    )
    if not raw_full_paths:
        raise ValueError(
            "No directories to scan; configure 'full_paths' or pass 'full_paths' argument"
        )

    full_paths_normalised = normalise_paths(root, raw_full_paths)
    engines = resolve_engines(audit_config.runners)
    # Resolve tool versions once to incorporate into cache keys
    tool_versions = detect_tool_versions([e.name for e in engines])
    cache = EngineCache(root)
    fingerprint_truncated_any = False

    runs: list[RunResult] = []
    for engine in engines:
        engine_options = resolve_engine_options(root, audit_config, engine)
        for mode in ("current", "full"):
            if mode == "current" and audit_config.skip_current:
                continue
            if mode == "full" and audit_config.skip_full:
                continue

            context = EngineContext(
                project_root=root,
                audit_config=audit_config,
                mode=mode,
                engine_options=engine_options,
            )
            run_result, truncated = execute_engine_mode(
                engine=engine,
                mode=mode,
                context=context,
                audit_config=audit_config,
                cache=cache,
                tool_versions=tool_versions,
                root=root,
                full_paths_normalised=full_paths_normalised,
            )
            runs.append(run_result)
            if truncated:
                fingerprint_truncated_any = True

    cache.save()

    builder = ManifestBuilder(root)
    builder.fingerprint_truncated = fingerprint_truncated_any
    depth = audit_config.max_depth or 3
    for run in runs:
        builder.add_run(run, max_depth=depth)
    manifest = builder.data

    manifest_target = write_manifest_to or audit_config.manifest_path
    if manifest_target is not None:
        out = manifest_target if manifest_target.is_absolute() else (root / manifest_target)
        builder.write(out)

    should_build_summary = (
        build_summary_output
        or audit_config.dashboard_json
        or audit_config.dashboard_markdown
        or audit_config.dashboard_html
    )
    summary = build_summary(manifest) if should_build_summary else None

    if summary is not None:
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

    error_count = sum(run.severity_counts().get("error", 0) for run in runs)
    warning_count = sum(run.severity_counts().get("warning", 0) for run in runs)

    return AuditResult(
        manifest=manifest,
        runs=runs,
        summary=summary if build_summary_output else None,
        error_count=error_count,
        warning_count=warning_count,
    )
