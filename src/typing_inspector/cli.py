from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Iterable, Sequence

from .config import load_config
from .dashboard import build_summary, load_manifest, render_markdown
from .html_report import render_html
from .manifest import ManifestBuilder
from .runner import run_mypy, run_pyright
from .types import RunResult
from .utils import default_full_paths, python_executable, resolve_project_root


def _pyright_current_command(extra_args: Sequence[str]) -> list[str]:
    command = ["pyright", "--outputjson", "--project", "pyrightconfig.json"]
    command.extend(extra_args)
    return command


def _pyright_full_command(paths: Sequence[str], extra_args: Sequence[str]) -> list[str]:
    command = ["pyright", "--outputjson"]
    command.extend(extra_args)
    command.extend(paths)
    return command


def _mypy_current_command(extra_args: Sequence[str]) -> list[str]:
    command = [
        python_executable(),
        "-m",
        "mypy",
        "--config-file",
        "mypy.ini",
        "--no-pretty",
    ]
    command.extend(extra_args)
    return command


def _mypy_full_command(paths: Sequence[str], extra_args: Sequence[str]) -> list[str]:
    command = [
        python_executable(),
        "-m",
        "mypy",
        "--config-file",
        "mypy.ini",
        "--hide-error-context",
        "--no-error-summary",
        "--show-error-codes",
        "--no-pretty",
    ]
    command.extend(extra_args)
    command.extend(paths)
    return command


def _print_summary(runs: Iterable[RunResult]) -> None:
    for run in runs:
        counts = run.severity_counts()
        summary = f"errors={counts.get('error', 0)} warnings={counts.get('warning', 0)} info={counts.get('information', 0)}"
        cmd = " ".join(shlex.quote(arg) for arg in run.command)
        print(f"[typing-inspector] {run.tool}:{run.mode} exit={run.exit_code} {summary} ({cmd})")


def _resolve_output_path(project_root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else (project_root / path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="typing-inspector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Collect typing diagnostics and produce a manifest")
    audit.add_argument("--config", type=Path, default=None, help="Path to typing_inspector.toml config")
    audit.add_argument("--project-root", type=Path, default=None)
    audit.add_argument("--manifest", type=Path, default=None, help="Override manifest output path")
    audit.add_argument("--full-path", dest="full_paths", action="append", default=[], help="Additional paths for full runs")
    audit.add_argument("--max-depth", type=int, default=None, help="Folder aggregation depth")
    audit.add_argument("--skip-current", dest="skip_current", action=argparse.BooleanOptionalAction, default=None)
    audit.add_argument("--skip-full", dest="skip_full", action=argparse.BooleanOptionalAction, default=None)
    audit.add_argument("--pyright-only", dest="pyright_only", action=argparse.BooleanOptionalAction, default=None)
    audit.add_argument("--mypy-only", dest="mypy_only", action=argparse.BooleanOptionalAction, default=None)
    audit.add_argument("--pyright-arg", action="append", default=[], help="Extra argument for pyright (repeatable)")
    audit.add_argument("--mypy-arg", action="append", default=[], help="Extra argument for mypy (repeatable)")
    audit.add_argument(
        "--fail-on",
        choices=["never", "warnings", "errors"],
        default=None,
        help="Return non-zero when diagnostics reach this severity",
    )
    audit.add_argument("--dashboard-json", type=Path, default=None, help="Optional dashboard JSON output path")
    audit.add_argument("--dashboard-markdown", type=Path, default=None, help="Optional dashboard Markdown output path")
    audit.add_argument("--dashboard-html", type=Path, default=None, help="Optional dashboard HTML output path")

    dashboard = subparsers.add_parser("dashboard", help="Render a summary from an existing manifest")
    dashboard.add_argument("--manifest", type=Path, required=True, help="Path to a typing audit manifest")
    dashboard.add_argument(
        "--format",
        choices=["json", "markdown", "html"],
        default="json",
        help="Output format (default: json)",
    )
    dashboard.add_argument("--output", type=Path, default=None, help="Optional output file")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "audit":
        config = load_config(args.config)
        project_root = resolve_project_root(args.project_root)

        def apply_bool(flag_value: bool | None, config_value: bool | None, default: bool) -> bool:
            if flag_value is not None:
                return flag_value
            if config_value is not None:
                return config_value
            return default

        manifest_path = _resolve_output_path(
            project_root,
            args.manifest or config.audit.manifest_path,
        ) or (project_root / "typing_audit_manifest.json")

        cli_full_paths = [path for entry in args.full_paths for path in entry.split(",") if path]
        full_paths = cli_full_paths or config.audit.full_paths or default_full_paths(project_root)
        if not full_paths:
            raise SystemExit("No paths found for full runs. Provide --full-path or configure full_paths.")

        max_depth = args.max_depth or config.audit.max_depth or 3

        skip_current = apply_bool(args.skip_current, config.audit.skip_current, default=False)
        skip_full = apply_bool(args.skip_full, config.audit.skip_full, default=False)
        pyright_only = apply_bool(args.pyright_only, config.audit.pyright_only, default=False)
        mypy_only = apply_bool(args.mypy_only, config.audit.mypy_only, default=False)

        pyright_args = (config.audit.pyright_args or []) + (args.pyright_arg or [])
        mypy_args = (config.audit.mypy_args or []) + (args.mypy_arg or [])
        fail_on = (args.fail_on or config.audit.fail_on or "never").lower()

        dashboard_json = _resolve_output_path(project_root, args.dashboard_json or config.audit.dashboard_json)
        dashboard_md = _resolve_output_path(project_root, args.dashboard_markdown or config.audit.dashboard_markdown)
        dashboard_html = _resolve_output_path(project_root, args.dashboard_html or config.audit.dashboard_html)

        runs: list[RunResult] = []

        if not skip_current and not mypy_only:
            runs.append(
                run_pyright(
                    project_root,
                    mode="current",
                    command=_pyright_current_command(pyright_args),
                )
            )
        if not skip_full and not mypy_only:
            runs.append(
                run_pyright(
                    project_root,
                    mode="full",
                    command=_pyright_full_command(full_paths, pyright_args),
                )
            )
        if not skip_current and not pyright_only:
            runs.append(
                run_mypy(
                    project_root,
                    mode="current",
                    command=_mypy_current_command(mypy_args),
                )
            )
        if not skip_full and not pyright_only:
            runs.append(
                run_mypy(
                    project_root,
                    mode="full",
                    command=_mypy_full_command(full_paths, mypy_args),
                )
            )

        builder = ManifestBuilder(project_root)
        for run in runs:
            builder.add_run(run, max_depth=max_depth)
        builder.write(manifest_path)

        summary_data = builder.data

        if dashboard_json or dashboard_md or dashboard_html:
            summary = build_summary(summary_data)
            if dashboard_json:
                dashboard_json.parent.mkdir(parents=True, exist_ok=True)
                dashboard_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            if dashboard_md:
                dashboard_md.parent.mkdir(parents=True, exist_ok=True)
                dashboard_md.write_text(render_markdown(summary), encoding="utf-8")
            if dashboard_html:
                dashboard_html.parent.mkdir(parents=True, exist_ok=True)
                dashboard_html.write_text(render_html(summary), encoding="utf-8")

        _print_summary(runs)

        error_count = sum(run.severity_counts().get("error", 0) for run in runs)
        warning_count = sum(run.severity_counts().get("warning", 0) for run in runs)

        if fail_on == "errors" and error_count > 0:
            return 2
        if fail_on == "warnings" and (error_count > 0 or warning_count > 0):
            return 2
        return 0

    if args.command == "dashboard":
        manifest = load_manifest(args.manifest)
        summary = build_summary(manifest)
        if args.format == "json":
            rendered = json.dumps(summary, indent=2) + "\n"
        elif args.format == "markdown":
            rendered = render_markdown(summary)
        else:
            rendered = render_html(summary)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")

        return 0

    return 0
