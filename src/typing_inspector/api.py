from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence

from .config import AuditConfig, Config, load_config
from .dashboard import build_summary
from .typed_manifest import ManifestData
from .manifest import ManifestBuilder
from .runner import run_mypy, run_pyright
from .types import RunResult
from .utils import default_full_paths, python_executable, resolve_project_root


@dataclass(slots=True)
class AuditResult:
    manifest: ManifestData
    runs: list[RunResult]
    summary: dict[str, Any] | None = None


def _pyright_current_command(extra_args: Sequence[str]) -> list[str]:
    return ["pyright", "--outputjson", "--project", "pyrightconfig.json", *extra_args]


def _pyright_full_command(paths: Sequence[str], extra_args: Sequence[str]) -> list[str]:
    return ["pyright", "--outputjson", *extra_args, *paths]


def _mypy_current_command(extra_args: Sequence[str]) -> list[str]:
    return [
        python_executable(),
        "-m",
        "mypy",
        "--config-file",
        "mypy.ini",
        "--no-pretty",
        *extra_args,
    ]


def _mypy_full_command(paths: Sequence[str], extra_args: Sequence[str]) -> list[str]:
    return [
        python_executable(),
        "-m",
        "mypy",
        "--config-file",
        "mypy.ini",
        "--hide-error-context",
        "--no-error-summary",
        "--show-error-codes",
        "--no-pretty",
        *extra_args,
        *paths,
    ]


def run_audit(
    *,
    project_root: Path | None = None,
    config: Config | None = None,
    override: AuditConfig | None = None,
    full_paths: Sequence[str] | None = None,
    write_manifest_to: Path | None = None,
    build_summary_output: bool = False,
) -> AuditResult:
    """Run a typing audit programmatically.

    - Resolves configuration from typing_inspector.toml if not provided.
    - Executes pyright/mypy current and full runs (unless skipped).
    - Returns the manifest data structure and optionally includes a summary.
    - Optionally writes the manifest to disk.
    """

    cfg = config or load_config(None)
    ac = cfg.audit
    if override:
        # Merge simple overrides
        ac = AuditConfig(
            manifest_path=override.manifest_path or ac.manifest_path,
            full_paths=override.full_paths or ac.full_paths,
            max_depth=override.max_depth or ac.max_depth,
            skip_current=override.skip_current if override.skip_current is not None else ac.skip_current,
            skip_full=override.skip_full if override.skip_full is not None else ac.skip_full,
            pyright_only=override.pyright_only if override.pyright_only is not None else ac.pyright_only,
            mypy_only=override.mypy_only if override.mypy_only is not None else ac.mypy_only,
            pyright_args=(ac.pyright_args or []) + (override.pyright_args or []),
            mypy_args=(ac.mypy_args or []) + (override.mypy_args or []),
            fail_on=override.fail_on or ac.fail_on,
            dashboard_json=override.dashboard_json or ac.dashboard_json,
            dashboard_markdown=override.dashboard_markdown or ac.dashboard_markdown,
            dashboard_html=override.dashboard_html or ac.dashboard_html,
        )
    else:
        ac = ac

    root = resolve_project_root(project_root)

    # Compute paths
    fp = list(full_paths) if full_paths else (ac.full_paths or default_full_paths(root))
    if not fp:
        raise ValueError("No directories to scan; configure 'full_paths' or pass 'full_paths' argument")

    skip_current = bool(ac.skip_current)
    skip_full = bool(ac.skip_full)
    pyright_only = bool(ac.pyright_only)
    mypy_only = bool(ac.mypy_only)

    runs: list[RunResult] = []
    if not skip_current and not mypy_only:
        runs.append(run_pyright(root, mode="current", command=_pyright_current_command(ac.pyright_args)))
    if not skip_full and not mypy_only:
        runs.append(run_pyright(root, mode="full", command=_pyright_full_command(fp, ac.pyright_args)))
    if not skip_current and not pyright_only:
        runs.append(run_mypy(root, mode="current", command=_mypy_current_command(ac.mypy_args)))
    if not skip_full and not pyright_only:
        runs.append(run_mypy(root, mode="full", command=_mypy_full_command(fp, ac.mypy_args)))

    builder = ManifestBuilder(root)
    depth = ac.max_depth or 3
    for run in runs:
        builder.add_run(run, max_depth=depth)
    manifest = builder.data

    target_manifest = write_manifest_to or ac.manifest_path
    if target_manifest is not None:
        out = target_manifest if target_manifest.is_absolute() else (root / target_manifest)
        out.parent.mkdir(parents=True, exist_ok=True)
        builder.write(out)

    summary = build_summary(manifest) if (build_summary_output or ac.dashboard_json or ac.dashboard_markdown or ac.dashboard_html) else None

    if summary is not None:
        if ac.dashboard_json:
            target = ac.dashboard_json if ac.dashboard_json.is_absolute() else (root / ac.dashboard_json)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if ac.dashboard_markdown:
            from .dashboard import render_markdown

            target = ac.dashboard_markdown if ac.dashboard_markdown.is_absolute() else (root / ac.dashboard_markdown)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_markdown(summary), encoding="utf-8")
        if ac.dashboard_html:
            from .html_report import render_html

            target = ac.dashboard_html if ac.dashboard_html.is_absolute() else (root / ac.dashboard_html)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_html(summary), encoding="utf-8")

    return AuditResult(manifest=manifest, runs=runs, summary=summary if build_summary_output else None)
