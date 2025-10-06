from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Dict, List, Sequence

from .api import run_audit
from .config import AuditConfig, load_config
from .dashboard import build_summary, load_manifest, render_markdown
from .html_report import render_html
from .types import RunResult
from .utils import default_full_paths, resolve_project_root


def _print_summary(runs: Sequence[RunResult]) -> None:
    for run in runs:
        counts = run.severity_counts()
        summary = f"errors={counts.get('error', 0)} warnings={counts.get('warning', 0)} info={counts.get('information', 0)}"
        cmd = " ".join(shlex.quote(arg) for arg in run.command)
        print(f"[pytc] {run.tool}:{run.mode} exit={run.exit_code} {summary} ({cmd})")


def _parse_plugin_args(values: Sequence[str]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for raw in values:
        if "=" not in raw:
            raise SystemExit(f"Invalid --plugin-arg value '{raw}'. Expected format runner=ARG")
        runner, arg = raw.split("=", 1)
        runner = runner.strip()
        if not runner:
            raise SystemExit("Runner name in --plugin-arg cannot be empty")
        result.setdefault(runner, []).append(arg.strip())
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pytc")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Collect typing diagnostics and produce a manifest")
    audit.add_argument("--config", type=Path, default=None, help="Path to pytc.toml config")
    audit.add_argument("--project-root", type=Path, default=None)
    audit.add_argument("--manifest", type=Path, default=None, help="Override manifest output path")
    audit.add_argument("--full-path", dest="full_paths", action="append", default=[], help="Additional paths for full runs")
    audit.add_argument("--runner", dest="runners", action="append", default=None, help="Specify runners to execute")
    audit.add_argument("--max-depth", type=int, default=None, help="Folder aggregation depth")
    audit.add_argument("--skip-current", dest="skip_current", action=argparse.BooleanOptionalAction, default=None)
    audit.add_argument("--skip-full", dest="skip_full", action=argparse.BooleanOptionalAction, default=None)
    audit.add_argument("--pyright-arg", action="append", default=[], help="Extra argument for pyright (repeatable)")
    audit.add_argument("--mypy-arg", action="append", default=[], help="Extra argument for mypy (repeatable)")
    audit.add_argument("--plugin-arg", action="append", default=[], help="Runner-specific argument (runner=ARG)")
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

        cli_full_paths = [path for entry in args.full_paths for path in entry.split(",") if path]
        selected_full_paths = cli_full_paths or config.audit.full_paths or default_full_paths(project_root)
        if not selected_full_paths:
            raise SystemExit("No paths found for full runs. Provide --full-path or configure full_paths.")

        override = AuditConfig(
            manifest_path=args.manifest,
            full_paths=cli_full_paths or None,
            max_depth=args.max_depth,
            skip_current=args.skip_current,
            skip_full=args.skip_full,
            fail_on=args.fail_on,
            dashboard_json=args.dashboard_json,
            dashboard_markdown=args.dashboard_markdown,
            dashboard_html=args.dashboard_html,
            runners=args.runners,
        )
        if args.pyright_arg:
            override.plugin_args["pyright"] = list(args.pyright_arg)
        if args.mypy_arg:
            override.plugin_args["mypy"] = list(args.mypy_arg)
        if args.plugin_arg:
            plugin_arg_map = _parse_plugin_args(args.plugin_arg)
            for name, values in plugin_arg_map.items():
                override.plugin_args.setdefault(name, []).extend(values)

        manifest_target = args.manifest if args.manifest else None
        result = run_audit(
            project_root=project_root,
            config=config,
            override=override,
            full_paths=selected_full_paths,
            write_manifest_to=manifest_target,
            build_summary_output=True,
        )

        _print_summary(result.runs)
        summary = result.summary or build_summary(result.manifest)

        fail_on = (args.fail_on or config.audit.fail_on or "never").lower()
        error_count = sum(run.severity_counts().get("error", 0) for run in result.runs)
        warning_count = sum(run.severity_counts().get("warning", 0) for run in result.runs)

        exit_code = 0
        if fail_on == "errors" and error_count > 0:
            exit_code = 2
        elif fail_on == "warnings" and (error_count > 0 or warning_count > 0):
            exit_code = 2

        # If summary outputs not generated by run_audit (when no destinations configured), allow CLI options to write them
        if args.dashboard_json and not args.dashboard_json.exists():
            args.dashboard_json.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if args.dashboard_markdown and not args.dashboard_markdown.exists():
            args.dashboard_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_markdown.write_text(render_markdown(summary), encoding="utf-8")
        if args.dashboard_html and not args.dashboard_html.exists():
            args.dashboard_html.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_html.write_text(render_html(summary), encoding="utf-8")

        return exit_code

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
