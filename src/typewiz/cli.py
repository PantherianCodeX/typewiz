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


SUMMARY_FIELD_CHOICES = {"profile", "config", "plugin-args", "paths", "overrides"}


def _format_list(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "—"


def _parse_summary_fields(raw: str | None) -> list[str]:
    if not raw:
        return []
    fields: list[str] = []
    for part in raw.split(","):
        item = part.strip().lower()
        if not item:
            continue
        if item == "all":
            return sorted(SUMMARY_FIELD_CHOICES)
        if item not in SUMMARY_FIELD_CHOICES:
            raise SystemExit(
                f"Unknown summary field '{item}'. "
                f"Valid values: {', '.join(sorted(SUMMARY_FIELD_CHOICES | {'all'}))}"
            )
        if item not in fields:
            fields.append(item)
    return fields


def _print_summary(
    runs: Sequence[RunResult],
    fields: Sequence[str],
    style: str,
) -> None:
    field_set = set(fields)

    for run in runs:
        counts = run.severity_counts()
        summary = (
            f"errors={counts.get('error', 0)} "
            f"warnings={counts.get('warning', 0)} "
            f"info={counts.get('information', 0)}"
        )
        cmd = " ".join(shlex.quote(arg) for arg in run.command)

        detail_items: list[tuple[str, str]] = []
        if "profile" in field_set:
            if run.profile:
                detail_items.append(("profile", run.profile))
            elif style == "expanded":
                detail_items.append(("profile", "—"))
        if "config" in field_set:
            if run.config_file:
                detail_items.append(("config", str(run.config_file)))
            elif style == "expanded":
                detail_items.append(("config", "—"))
        if "plugin-args" in field_set:
            plugin_args = _format_list(list(run.plugin_args))
            if plugin_args != "—" or style == "expanded":
                detail_items.append(("plugin args", plugin_args))
        if "paths" in field_set:
            include_paths = _format_list(list(run.include))
            exclude_paths = _format_list(list(run.exclude))
            if include_paths != "—" or style == "expanded":
                detail_items.append(("include", include_paths))
            if exclude_paths != "—" or style == "expanded":
                detail_items.append(("exclude", exclude_paths))
        overrides_data = [dict(item) for item in run.overrides]
        if "overrides" in field_set and overrides_data:
            if style == "expanded":
                for entry in overrides_data:
                    label = f"override {entry.get('path', '—')}"
                    parts: list[str] = []
                    if entry.get("profile"):
                        parts.append(f"profile={entry['profile']}")
                    if entry.get("pluginArgs"):
                        parts.append(
                            "plugin args=" + ", ".join(entry.get("pluginArgs", []))
                        )
                    if entry.get("include"):
                        parts.append(
                            "include=" + ", ".join(entry.get("include", []))
                        )
                    if entry.get("exclude"):
                        parts.append(
                            "exclude=" + ", ".join(entry.get("exclude", []))
                        )
                    detail = "; ".join(parts) if parts else "no explicit changes"
                    detail_items.append((label, detail))
            else:
                short = []
                for entry in overrides_data:
                    parts: list[str] = []
                    if entry.get("profile"):
                        parts.append(f"profile={entry['profile']}")
                    if entry.get("pluginArgs"):
                        parts.append(
                            "args=" + "/".join(entry.get("pluginArgs", []))
                        )
                    short.append(
                        f"{entry.get('path', '—')}" + (f"({', '.join(parts)})" if parts else "")
                    )
                detail_items.append(("overrides", "; ".join(short)))

        header = f"[typewiz] {run.tool}:{run.mode} exit={run.exit_code} {summary} ({cmd})"

        if style == "expanded" and detail_items:
            print(header)
            for label, value in detail_items:
                print(f"           - {label}: {value}")
        else:
            if detail_items:
                inline = " ".join(f"{label}={value}" for label, value in detail_items)
                print(f"{header} [{inline}]")
            else:
                print(header)


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


def _parse_profile_args(values: Sequence[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise SystemExit(f"Invalid --profile value '{raw}'. Expected format runner=PROFILE")
        runner, profile = raw.split("=", 1)
        runner = runner.strip()
        profile = profile.strip()
        if not runner or not profile:
            raise SystemExit("--profile entries must specify both runner and profile")
        result[runner] = profile
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="typewiz")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Collect typing diagnostics and produce a manifest")
    audit.add_argument("--config", type=Path, default=None, help="Path to typewiz.toml config")
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
    audit.add_argument("--profile", action="append", default=[], help="Select an engine profile (runner=PROFILE)")
    audit.add_argument(
        "-S",
        "--summary",
        choices=["compact", "expanded", "full"],
        default="compact",
        help="Compact (default), expanded (multi-line), or full (expanded + all fields)",
    )
    audit.add_argument(
        "--summary-fields",
        default=None,
        help="Comma-separated extra summary fields "
        "(profile, config, plugin-args, paths, all). Ignored when --summary=full.",
    )
    audit.add_argument(
        "--fail-on",
        choices=["never", "warnings", "errors"],
        default=None,
        help="Return non-zero when diagnostics reach this severity",
    )
    audit.add_argument("--dashboard-json", type=Path, default=None, help="Optional dashboard JSON output path")
    audit.add_argument("--dashboard-markdown", type=Path, default=None, help="Optional dashboard Markdown output path")
    audit.add_argument("--dashboard-html", type=Path, default=None, help="Optional dashboard HTML output path")
    audit.add_argument(
        "--dashboard-view",
        choices=["overview", "engines", "hotspots", "runs"],
        default="overview",
        help="Default tab when writing the HTML dashboard",
    )

    dashboard = subparsers.add_parser("dashboard", help="Render a summary from an existing manifest")
    dashboard.add_argument("--manifest", type=Path, required=True, help="Path to a typing audit manifest")
    dashboard.add_argument(
        "--format",
        choices=["json", "markdown", "html"],
        default="json",
        help="Output format (default: json)",
    )
    dashboard.add_argument("--output", type=Path, default=None, help="Optional output file")
    dashboard.add_argument(
        "--view",
        choices=["overview", "engines", "hotspots", "runs"],
        default="overview",
        help="Default tab for HTML output",
    )

    readiness = subparsers.add_parser("readiness", help="Show top-N candidates for strict typing")
    readiness.add_argument("--manifest", type=Path, required=True, help="Path to a typing audit manifest")
    readiness.add_argument("--level", choices=["folder", "file"], default="folder")
    readiness.add_argument("--status", choices=["ready", "close", "blocked"], default="close")
    readiness.add_argument("--limit", type=int, default=10)

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
        if args.profile:
            override.active_profiles.update(_parse_profile_args(args.profile))

        summary_choice: str = args.summary
        summary_style = "expanded" if summary_choice in {"expanded", "full"} else "compact"
        summary_fields: list[str]
        if summary_choice == "full":
            summary_fields = sorted(SUMMARY_FIELD_CHOICES)
        else:
            summary_fields = _parse_summary_fields(args.summary_fields)

        manifest_target = args.manifest if args.manifest else None
        result = run_audit(
            project_root=project_root,
            config=config,
            override=override,
            full_paths=selected_full_paths,
            write_manifest_to=manifest_target,
            build_summary_output=True,
        )

        _print_summary(result.runs, summary_fields, summary_style)
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
        if args.dashboard_json:
            args.dashboard_json.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if args.dashboard_markdown:
            args.dashboard_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_markdown.write_text(render_markdown(summary), encoding="utf-8")
        if args.dashboard_html:
            args.dashboard_html.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_html.write_text(
                render_html(summary, default_view=args.dashboard_view),
                encoding="utf-8",
            )

        return exit_code

    if args.command == "dashboard":
        manifest = load_manifest(args.manifest)
        summary = build_summary(manifest)
        if args.format == "json":
            rendered = json.dumps(summary, indent=2) + "\n"
        elif args.format == "markdown":
            rendered = render_markdown(summary)
        else:
            rendered = render_html(summary, default_view=args.view)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")

        return 0

    if args.command == "readiness":
        manifest = load_manifest(args.manifest)
        summary = build_summary(manifest)
        if args.level == "folder":
            readiness_tab = summary.get("tabs", {}).get("readiness", {})
            strict = readiness_tab.get("strict", {})
            candidates = strict.get(args.status, [])
            # Sort by diagnostics then path
            candidates = sorted(candidates, key=lambda e: (e.get("diagnostics", 0), e.get("path", "")))
            for entry in candidates[: args.limit]:
                notes = ", ".join(entry.get("notes", []) or entry.get("recommendations", []))
                print(f"{entry['path']}  diag={entry.get('diagnostics', 0)}  notes={notes}")
            return 0

        # per-file readiness: aggregate diagnostics across runs
        from collections import defaultdict
        from .readiness import compute_readiness

        file_map: dict[str, dict[str, Any]] = {}
        for run in manifest.get("runs", []):
            for f in run.get("perFile", []):
                path = f.get("path")
                if not path:
                    continue
                cur = file_map.setdefault(
                    path,
                    {"path": path, "errors": 0, "warnings": 0, "information": 0, "codeCounts": defaultdict(int)},
                )
                cur["errors"] += f.get("errors", 0)
                cur["warnings"] += f.get("warnings", 0)
                cur["information"] += f.get("information", 0)
                for d in f.get("diagnostics", []):
                    code = d.get("code") or ""
                    if code:
                        cur["codeCounts"][code] += 1
        entries = []
        for v in file_map.values():
            v["codeCounts"] = dict(v["codeCounts"])  # flatten
            entries.append(v)
        readiness = compute_readiness(entries)
        strict = readiness.get("strict", {})
        candidates = strict.get(args.status, [])
        candidates = sorted(candidates, key=lambda e: (e.get("diagnostics", 0), e.get("path", "")))
        for entry in candidates[: args.limit]:
            notes = ", ".join(entry.get("notes", []) or entry.get("recommendations", []))
            print(f"{entry['path']}  diag={entry.get('diagnostics', 0)}  notes={notes}")
        return 0

    return 0
