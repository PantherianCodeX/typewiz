from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from .config import AuditConfig, Config, load_config, normalize_plugin_args
from .dashboard import build_summary, render_markdown
from .html_report import render_html
from .manifest import ManifestBuilder
from .plugins import PluginContext, resolve_runners
from .typed_manifest import ManifestData
from .types import RunResult
from .utils import default_full_paths, resolve_project_root

logger = logging.getLogger("pytc")


@dataclass(slots=True)
class AuditResult:
    manifest: ManifestData
    runs: list[RunResult]
    summary: dict[str, object] | None = None
    error_count: int = 0
    warning_count: int = 0


from dataclasses import fields


def _clone_config(source: AuditConfig) -> AuditConfig:
    copy = replace(source)
    copy.full_paths = list(source.full_paths) if source.full_paths is not None else None
    copy.pyright_args = list(source.pyright_args)
    copy.mypy_args = list(source.mypy_args)
    copy.plugin_args = {k: list(v) for k, v in source.plugin_args.items()}
    return copy


def _merge_configs(base: AuditConfig, override: AuditConfig | None) -> AuditConfig:
    base_copy = _clone_config(base)
    if override is None:
        normalize_plugin_args(base_copy)
        return base_copy

    merged = AuditConfig(
        manifest_path=override.manifest_path or base.manifest_path,
        full_paths=override.full_paths or base.full_paths,
        max_depth=override.max_depth or base.max_depth,
        skip_current=override.skip_current if override.skip_current is not None else base.skip_current,
        skip_full=override.skip_full if override.skip_full is not None else base.skip_full,
        pyright_args=(base_copy.pyright_args or []) + (override.pyright_args or []),
        mypy_args=(base_copy.mypy_args or []) + (override.mypy_args or []),
        fail_on=override.fail_on or base.fail_on,
        dashboard_json=override.dashboard_json or base.dashboard_json,
        dashboard_markdown=override.dashboard_markdown or base.dashboard_markdown,
        dashboard_html=override.dashboard_html or base.dashboard_html,
        runners=override.runners or base.runners,
    )
    merged.plugin_args = {k: list(v) for k, v in base_copy.plugin_args.items()}
    for name, values in override.plugin_args.items():
        merged.plugin_args.setdefault(name, []).extend(values)
    normalize_plugin_args(merged)
    return merged


def run_audit(
    *,
    project_root: Path | None = None,
    config: Config | None = None,
    override: AuditConfig | None = None,
    full_paths: Sequence[str] | None = None,
    write_manifest_to: Path | None = None,
    build_summary_output: bool = False,
) -> AuditResult:
    cfg = config or load_config(None)
    audit_config = _merge_configs(cfg.audit, override)

    root = resolve_project_root(project_root)
    selected_full_paths = list(full_paths) if full_paths else (audit_config.full_paths or default_full_paths(root))
    if not selected_full_paths:
        raise ValueError("No directories to scan; configure 'full_paths' or pass 'full_paths' argument")

    selected_runners = audit_config.runners or ["pyright", "mypy"]
    runners = resolve_runners(selected_runners)
    context = PluginContext(project_root=root, full_paths=selected_full_paths, audit_config=audit_config)

    runs: list[RunResult] = []
    for runner in runners:
        for command in runner.generate_commands(context):
            if command.mode == "current" and audit_config.skip_current:
                continue
            if command.mode == "full" and audit_config.skip_full:
                continue
            logger.info("Running %s (%s)", runner.name, " ".join(command.command))
            runs.append(runner.execute(context, command))

    builder = ManifestBuilder(root)
    depth = audit_config.max_depth or 3
    for run in runs:
        builder.add_run(run, max_depth=depth)
    manifest = builder.data

    manifest_target = write_manifest_to or audit_config.manifest_path
    if manifest_target is not None:
        out = manifest_target if manifest_target.is_absolute() else (root / manifest_target)
        builder.write(out)

    should_build_summary = build_summary_output or audit_config.dashboard_json or audit_config.dashboard_markdown or audit_config.dashboard_html
    summary = build_summary(manifest) if should_build_summary else None

    if summary is not None:
        if audit_config.dashboard_json:
            target = audit_config.dashboard_json if audit_config.dashboard_json.is_absolute() else (root / audit_config.dashboard_json)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if audit_config.dashboard_markdown:
            target = audit_config.dashboard_markdown if audit_config.dashboard_markdown.is_absolute() else (root / audit_config.dashboard_markdown)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_markdown(summary), encoding="utf-8")
        if audit_config.dashboard_html:
            target = audit_config.dashboard_html if audit_config.dashboard_html.is_absolute() else (root / audit_config.dashboard_html)
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
