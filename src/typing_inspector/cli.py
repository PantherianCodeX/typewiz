from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from typing import Iterable, Sequence

from .manifest import ManifestBuilder
from .runner import run_mypy, run_pyright
from .types import RunResult
from .utils import default_full_paths, python_executable, resolve_project_root


def _pyright_current_command(project_root: Path) -> list[str]:
    return ["pyright", "--outputjson", "--project", "pyrightconfig.json"]


def _pyright_full_command(project_root: Path, paths: Sequence[str]) -> list[str]:
    if not paths:
        paths = default_full_paths(project_root)
    command = ["pyright", "--outputjson"]
    command.extend(paths)
    return command


def _mypy_current_command(project_root: Path) -> list[str]:
    return [
        python_executable(),
        "-m",
        "mypy",
        "--config-file",
        "mypy.ini",
        "--no-pretty",
    ]


def _mypy_full_command(project_root: Path, paths: Sequence[str]) -> list[str]:
    if not paths:
        paths = default_full_paths(project_root)
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
    command.extend(paths)
    return command


def _print_summary(runs: Iterable[RunResult]) -> None:
    for run in runs:
        counts = run.severity_counts()
        summary = f"errors={counts.get('error', 0)} warnings={counts.get('warning', 0)} info={counts.get('information', 0)}"
        cmd = " ".join(shlex.quote(arg) for arg in run.command)
        print(f"[typing-inspector] {run.tool}:{run.mode} exit={run.exit_code} {summary} ({cmd})")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="typing-inspector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Collect typing diagnostics and produce a manifest")
    audit.add_argument("--project-root", type=Path, default=None)
    audit.add_argument("--manifest", type=Path, default=None)
    audit.add_argument("--full-path", dest="full_paths", action="append", default=[])
    audit.add_argument("--max-depth", type=int, default=3)
    audit.add_argument("--skip-current", action="store_true")
    audit.add_argument("--skip-full", action="store_true")
    audit.add_argument("--pyright-only", action="store_true")
    audit.add_argument("--mypy-only", action="store_true")

    dashboard = subparsers.add_parser("dashboard", help="Render a summary from an existing manifest")
    dashboard.add_argument("--manifest", type=Path, required=True, help="Path to a typing audit manifest")
    dashboard.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json)",
    )
    dashboard.add_argument("--output", type=Path, default=None, help="Optional output file")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "audit":
        project_root = resolve_project_root(args.project_root)
        manifest_path = args.manifest or (project_root / "docs" / "typing" / "typing_audit_manifest.json")
        full_paths = [path for entry in args.full_paths for path in entry.split(",") if path] or default_full_paths(project_root)

        runs: list[RunResult] = []

        if not args.skip_current and not args.mypy_only:
            runs.append(
                run_pyright(
                    project_root,
                    mode="current",
                    command=_pyright_current_command(project_root),
                )
            )
        if not args.skip_full and not args.mypy_only:
            runs.append(
                run_pyright(
                    project_root,
                    mode="full",
                    command=_pyright_full_command(project_root, full_paths),
                )
            )
        if not args.skip_current and not args.pyright_only:
            runs.append(
                run_mypy(
                    project_root,
                    mode="current",
                    command=_mypy_current_command(project_root),
                )
            )
        if not args.skip_full and not args.pyright_only:
            runs.append(
                run_mypy(
                    project_root,
                    mode="full",
                    command=_mypy_full_command(project_root, full_paths),
                )
            )

        builder = ManifestBuilder(project_root)
        for run in runs:
            builder.add_run(run, max_depth=args.max_depth)
        builder.write(manifest_path)

        _print_summary(runs)
        return 0

    if args.command == "dashboard":
        from .dashboard import build_summary, load_manifest, render_markdown

        manifest = load_manifest(args.manifest)
        summary = build_summary(manifest)
        if args.format == "json":
            import json

            rendered = json.dumps(summary, indent=2) + "\n"
        else:
            rendered = render_markdown(summary)

        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")

        return 0

    return 0
