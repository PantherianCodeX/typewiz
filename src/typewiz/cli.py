from __future__ import annotations

import argparse
import json
import shlex
from collections.abc import Sequence
from pathlib import Path
from textwrap import dedent
from typing import Any, cast

from .api import run_audit
from .config import AuditConfig, load_config
from .dashboard import build_summary, load_manifest, render_markdown
from .html_report import render_html
from .types import RunResult
from .utils import default_full_paths, resolve_project_root

SUMMARY_FIELD_CHOICES = {"profile", "config", "plugin-args", "paths", "overrides"}

CONFIG_TEMPLATE = dedent(
    """\
    # typewiz configuration template
    # Save this file as typewiz.toml in the root of your project.
    config_version = 0

    [audit]
    # Uncomment and adjust to pin the directories scanned during full audits.
    # full_paths = ["src", "tests"]

    # Engines that run by default (pyright and mypy ship with typewiz).
    runners = ["pyright", "mypy"]

    # Configure failure thresholds or output destinations as needed:
    # fail_on = "warnings"           # choices: never, warnings, errors
    # manifest_path = "typewiz/manifest.json"
    # dashboard_json = "typewiz/dashboard.json"
    # dashboard_markdown = "typewiz/dashboard.md"
    # dashboard_html = "typewiz/dashboard.html"

    # Select default profiles per engine here, or via `typewiz audit --profile`.
    [audit.active_profiles]
    # pyright = "baseline"
    # mypy = "strict"

    # Per-engine settings apply globally.
    [audit.engines.pyright]
    # plugin_args = ["--verifytypes"]
    # include = ["packages/api"]
    # exclude = ["packages/legacy"]
    # config_file = "configs/pyrightconfig.json"

    [audit.engines.pyright.profiles.strict]
    # inherit = "baseline"
    # plugin_args = ["--strict"]

    [audit.engines.mypy]
    # plugin_args = ["--strict"]
    # include = ["src"]
    # config_file = "configs/mypy.ini"

    # To scope settings to a folder, create a typewiz.dir.toml file in that
    # directory. Example contents:
    #
    #   [active_profiles]
    #   pyright = "strict"
    #
    #   [engines.pyright]
    #   plugin_args = ["--warnings"]
    #   include = ["."]
    #   exclude = ["legacy"]
    #
    # Files named typewiz.dir.toml or .typewizdir.toml are discovered recursively.
    """
)


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
                    plugin_args_list = cast(list[str], entry.get("pluginArgs", []))
                    include_list = cast(list[str], entry.get("include", []))
                    exclude_list = cast(list[str], entry.get("exclude", []))
                    if plugin_args_list:
                        parts.append("plugin args=" + ", ".join(plugin_args_list))
                    if include_list:
                        parts.append("include=" + ", ".join(include_list))
                    if exclude_list:
                        parts.append("exclude=" + ", ".join(exclude_list))
                    detail = "; ".join(parts) if parts else "no explicit changes"
                    detail_items.append((label, detail))
            else:
                short: list[str] = []
                for entry in overrides_data:
                    parts_short: list[str] = []
                    if entry.get("profile"):
                        parts_short.append(f"profile={entry['profile']}")
                    plugin_args_list = cast(list[str], entry.get("pluginArgs", []))
                    if plugin_args_list:
                        parts_short.append("args=" + "/".join(plugin_args_list))
                    short.append(
                        f"{entry.get('path', '—')}"
                        + (f"({', '.join(parts_short)})" if parts_short else "")
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


def _collect_plugin_args(entries: Sequence[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for raw in entries:
        if "=" in raw:
            runner, arg = raw.split("=", 1)
        elif ":" in raw:
            runner, arg = raw.split(":", 1)
        else:
            raise SystemExit(f"Invalid --plugin-arg value '{raw}'. Use RUNNER=ARG (or RUNNER:ARG).")
        runner = runner.strip()
        if not runner:
            raise SystemExit("Runner name in --plugin-arg cannot be empty")
        arg = arg.strip()
        if not arg:
            raise SystemExit(f"Argument for runner '{runner}' cannot be empty")
        result.setdefault(runner, []).append(arg)
    return result


def _collect_profile_args(pairs: Sequence[Sequence[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in pairs:
        if len(entry) != 2:
            raise SystemExit("Each --profile option requires a runner and a profile name")
        runner, profile = entry
        runner = runner.strip()
        profile = profile.strip()
        if not runner or not profile:
            raise SystemExit("--profile entries must specify both runner and profile")
        result[runner] = profile
    return result


def _normalise_modes(modes: Sequence[str] | None) -> tuple[bool, bool, bool]:
    if not modes:
        return (False, True, True)
    requested = {mode.lower() for mode in modes}
    run_current = "current" in requested
    run_full = "full" in requested
    if not run_current and not run_full:
        raise SystemExit("No modes selected. Choose at least one of: current, full.")
    return (True, run_current, run_full)


def _write_config_template(path: Path, *, force: bool) -> int:
    if path.exists() and not force:
        print(f"[typewiz] Refusing to overwrite existing file: {path}")
        print("Use --force if you want to replace it.")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    print(f"[typewiz] Wrote starter config to {path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="typewiz",
        description="Collect typing diagnostics and readiness insights for Python projects.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser(
        "audit",
        help="Run typing audits and produce manifests/dashboards",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Collect diagnostics from configured engines and optionally write manifests or dashboards.",
    )
    audit.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="Directories to include in full runs (default: auto-detected python packages).",
    )
    audit.add_argument(
        "-C",
        "--config",
        type=Path,
        default=None,
        help="Path to a typewiz configuration file.",
    )
    audit.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory (defaults to the current working directory).",
    )
    audit.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Override the manifest output path.",
    )
    audit.add_argument(
        "-r",
        "--runner",
        dest="runners",
        action="append",
        metavar="NAME",
        default=None,
        help="Limit execution to the specified runner (repeatable).",
    )
    audit.add_argument(
        "-m",
        "--mode",
        dest="modes",
        action="append",
        choices=["current", "full"],
        help="Select which audit modes to run. Repeat to include multiple modes (default: both).",
    )
    audit.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Folder aggregation depth for summaries.",
    )
    audit.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum files to fingerprint for cache invalidation (protects giant repos).",
    )
    audit.add_argument(
        "--max-fingerprint-bytes",
        type=int,
        default=None,
        help="Upper bound on total bytes considered for fingerprinting (size budget).",
    )
    audit.add_argument(
        "--respect-gitignore",
        action="store_true",
        help="When fingerprinting, skip files ignored by .gitignore (requires git).",
    )
    audit.add_argument(
        "--plugin-arg",
        dest="plugin_arg",
        action="append",
        metavar="RUNNER=ARG",
        default=[],
        help="Pass an extra argument to a runner (repeatable). Example: --plugin-arg pyright=--verifytypes",
    )
    audit.add_argument(
        "--profile",
        dest="profiles",
        action="append",
        nargs=2,
        metavar=("RUNNER", "PROFILE"),
        default=[],
        help="Activate a named profile for a runner (repeatable).",
    )
    audit.add_argument(
        "-S",
        "--summary",
        choices=["compact", "expanded", "full"],
        default="compact",
        help="Compact (default), expanded (multi-line), or full (expanded + all fields).",
    )
    audit.add_argument(
        "--summary-fields",
        default=None,
        help="Comma-separated extra summary fields (profile, config, plugin-args, paths, all). Ignored for --summary=full.",
    )
    audit.add_argument(
        "--fail-on",
        choices=["none", "never", "warnings", "errors", "any"],
        default=None,
        help="Non-zero exit when diagnostics reach this severity (aliases: none=never, any=any finding).",
    )
    audit.add_argument(
        "--dashboard-json",
        type=Path,
        default=None,
        help="Optional dashboard JSON output path.",
    )
    audit.add_argument(
        "--dashboard-markdown",
        type=Path,
        default=None,
        help="Optional dashboard Markdown output path.",
    )
    audit.add_argument(
        "--dashboard-html",
        type=Path,
        default=None,
        help="Optional dashboard HTML output path.",
    )
    audit.add_argument(
        "--compare-to",
        type=Path,
        default=None,
        help="Optional path to a previous manifest to compare totals against (adds deltas to CI line).",
    )
    audit.add_argument(
        "--dashboard-view",
        choices=["overview", "engines", "hotspots", "runs"],
        default="overview",
        help="Default tab when writing the HTML dashboard.",
    )

    dashboard = subparsers.add_parser(
        "dashboard",
        help="Render a summary from an existing manifest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    dashboard.add_argument(
        "--manifest", type=Path, required=True, help="Path to a typing audit manifest."
    )
    dashboard.add_argument(
        "--format",
        choices=["json", "markdown", "html"],
        default="json",
        help="Output format.",
    )
    dashboard.add_argument("--output", type=Path, default=None, help="Optional output file.")
    dashboard.add_argument(
        "--view",
        choices=["overview", "engines", "hotspots", "runs"],
        default="overview",
        help="Default tab when generating HTML.",
    )

    manifest_cmd = subparsers.add_parser(
        "manifest",
        help="Work with manifest files (validate)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    manifest_sub = manifest_cmd.add_subparsers(dest="action", required=True)
    manifest_validate = manifest_sub.add_parser(
        "validate",
        help="Validate a manifest against the JSON schema",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    manifest_validate.add_argument("path", type=Path, help="Path to manifest file to validate")
    manifest_validate.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Explicit path to the JSON schema (defaults to bundled schema)",
    )

    init = subparsers.add_parser(
        "init",
        help="Generate a starter configuration file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    init.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("typewiz.toml"),
        help="Destination for the generated configuration file.",
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )

    readiness = subparsers.add_parser(
        "readiness",
        help="Show top-N candidates for strict typing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    readiness.add_argument(
        "--manifest", type=Path, required=True, help="Path to a typing audit manifest."
    )
    readiness.add_argument("--level", choices=["folder", "file"], default="folder")
    readiness.add_argument("--status", choices=["ready", "close", "blocked"], default="close")
    readiness.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "init":
        return _write_config_template(args.output, force=args.force)

    if args.command == "audit":
        config = load_config(args.config)
        project_root = resolve_project_root(args.project_root)

        cli_full_paths = [path for path in args.paths if path]
        selected_full_paths = (
            cli_full_paths or config.audit.full_paths or default_full_paths(project_root)
        )
        if not selected_full_paths:
            raise SystemExit(
                "No paths found for full runs. Provide paths or configure 'full_paths'."
            )

        modes_specified, run_current, run_full = _normalise_modes(args.modes)
        override = AuditConfig(
            manifest_path=args.manifest,
            full_paths=cli_full_paths or None,
            max_depth=args.max_depth,
            max_files=args.max_files,
            max_bytes=args.max_fingerprint_bytes,
            skip_current=(not run_current) if modes_specified else None,
            skip_full=(not run_full) if modes_specified else None,
            fail_on=args.fail_on,
            dashboard_json=args.dashboard_json,
            dashboard_markdown=args.dashboard_markdown,
            dashboard_html=args.dashboard_html,
            respect_gitignore=args.respect_gitignore,
            runners=args.runners,
        )
        if args.plugin_arg:
            plugin_arg_map = _collect_plugin_args(args.plugin_arg)
            for name, values in plugin_arg_map.items():
                override.plugin_args.setdefault(name, []).extend(values)
        if args.profiles:
            override.active_profiles.update(_collect_profile_args(args.profiles))

        summary_choice: str = args.summary
        summary_style = "expanded" if summary_choice in {"expanded", "full"} else "compact"
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
        from .summary_types import SummaryData

        summary: SummaryData = result.summary or build_summary(result.manifest)

        fail_on = (args.fail_on or config.audit.fail_on or "never").lower()
        error_count = sum(run.severity_counts().get("error", 0) for run in result.runs)
        warning_count = sum(run.severity_counts().get("warning", 0) for run in result.runs)
        info_count = sum(run.severity_counts().get("information", 0) for run in result.runs)

        # Optional deltas against a previous manifest
        delta_str = ""
        if args.compare_to and args.compare_to.exists():
            try:
                from .dashboard import load_manifest as _load_manifest

                prev_manifest = _load_manifest(args.compare_to)
                prev_summary = build_summary(prev_manifest)
                prev_sev = prev_summary["tabs"]["overview"]["severityTotals"]
                de = error_count - int(prev_sev.get("error", 0))
                dw = warning_count - int(prev_sev.get("warning", 0))
                di = info_count - int(prev_sev.get("information", 0))
                def _fmt(x: int) -> str:
                    return f"+{x}" if x > 0 else (f"{x}" if x < 0 else "0")
                delta_str = f"; delta: errors={_fmt(de)} warnings={_fmt(dw)} info={_fmt(di)}"
            except Exception:
                delta_str = ""

        exit_code = 0
        if fail_on in {"never", "none"}:
            exit_code = 0
        elif fail_on == "errors" and error_count > 0:
            exit_code = 2
        elif fail_on == "warnings" and (error_count > 0 or warning_count > 0):
            exit_code = 2
        elif fail_on == "any" and (error_count > 0 or warning_count > 0 or info_count > 0):
            exit_code = 2

        # Compact CI summary line
        print(f"[typewiz] totals: errors={error_count} warnings={warning_count} info={info_count}; runs={len(result.runs)}" + delta_str)

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
            if args.format == "json":
                print(rendered, end="")
            else:
                print(rendered)

        return 0

    if args.command == "manifest":
        action = args.action
        if action == "validate":
            manifest_path: Path = args.path
            schema_path = args.schema or Path("schemas/typing_audit_manifest.schema.json")
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            try:
                # Prefer jsonschema when available
                import importlib
                jsonschema: Any = importlib.import_module("jsonschema")
                validator = jsonschema.Draft7Validator(
                    json.loads(schema_path.read_text(encoding="utf-8"))
                )
                errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
                if errors:
                    for err in errors:
                        loc = "/".join(str(p) for p in err.path)
                        print(f"[typewiz] schema error at /{loc}: {err.message}")
                    return 2
                print("[typewiz] manifest is valid")
                return 0
            except ModuleNotFoundError:
                # Fallback: minimal structural check without dependency
                required = ["generatedAt", "projectRoot", "runs"]
                missing = [k for k in required if k not in data]
                if missing:
                    print(f"[typewiz] manifest missing required keys: {', '.join(missing)}")
                    return 2
                if not isinstance(data.get("runs"), list):
                    print("[typewiz] manifest.runs must be an array")
                    return 2
                print(
                    "[typewiz] manifest passes basic validation (install 'jsonschema' for full checks)"
                )
                return 0
        raise SystemExit("Unknown manifest action")

    if args.command == "readiness":
        manifest = load_manifest(args.manifest)
        from .summary_types import ReadinessOptionsBucket, ReadinessTab, SummaryData, SummaryTabs

        summary_map: SummaryData = build_summary(manifest)
        tabs: SummaryTabs = summary_map["tabs"]
        readiness_tab: ReadinessTab = tabs.get("readiness", {})
        options_tab = readiness_tab.get("options", {})
        # strict buckets are nested under readiness.strict

        if args.level == "folder":
            default_bucket: ReadinessOptionsBucket = {
                "ready": [],
                "close": [],
                "blocked": [],
                "threshold": 0,
            }
            bucket: ReadinessOptionsBucket = options_tab.get("unknownChecks", default_bucket)
            if args.status == "ready":
                status_bucket = bucket.get("ready", [])
            elif args.status == "close":
                status_bucket = bucket.get("close", [])
            else:
                status_bucket = bucket.get("blocked", [])
        else:
            status_bucket = readiness_tab.get("strict", {}).get(args.status, [])
        for entry in status_bucket[: args.limit]:
            path = entry.get("path", "<unknown>")
            count = entry.get("count") or entry.get("diagnostics") or 0
            print(f"{path}: {count}")

        return 0

    raise SystemExit(f"Unknown command {args.command}")
