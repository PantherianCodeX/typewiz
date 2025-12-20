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

"""CLI entrypoint for the s11r2 progress generator.

This command:
- discovers governance paths from `registers/registry_index.md`;
- loads the status legend from `STATUS_LEGEND.md`;
- validates all tracked registers;
- generates `progress/progress_board.md` and (optionally) the HTML dashboard.

No manual roll-ups are supported: outputs are fully derived from the canonical
registries.

Exit behavior is controlled by `--fail-on`:
- ERROR: fail if any ERROR issues exist (default).
- WARN: fail if any WARNING or ERROR issues exist.
- INFO: fail if any issues exist (INFO/WARN/ERROR).
- NEVER: never fail (always exit 0).

Implementation note:
To avoid noisy diffs, generation timestamps are only updated when the underlying
content changes (timestamps are treated as metadata).
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from typing_extensions import override

from scripts.docs.s11r2_progress.dashboard import DashboardLinks, DashboardRenderOptions, render_dashboard
from scripts.docs.s11r2_progress.legend import load_status_legend
from scripts.docs.s11r2_progress.metrics import compute_metrics
from scripts.docs.s11r2_progress.models import FailOn, Issue, IssueReport, Severity
from scripts.docs.s11r2_progress.paths import S11R2Paths, discover_paths
from scripts.docs.s11r2_progress.render import compose_progress_board_output

if TYPE_CHECKING:
    from collections.abc import Iterable

_LOGGER = logging.getLogger("s11r2-progress")


def _parse_fail_on(value: str) -> FailOn:
    """Parse a fail-on CLI argument into a FailOn enum.

    Args:
        value: Raw CLI value.

    Returns:
        Parsed FailOn enum.

    Raises:
        argparse.ArgumentTypeError: If the value is not a valid FailOn member.
    """
    v = value.strip().upper()
    try:
        return FailOn(v)
    # ignore JUSTIFIED: Defensive guard for argparse enum parsing.
    except ValueError as exc:  # pragma: no cover
        msg = f"Invalid fail-on value: {value!r}"
        raise argparse.ArgumentTypeError(msg) from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for s11r2 progress generation.

    Args:
        argv: CLI arguments (excluding the executable).

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(prog="s11r2-progress", description="Generate s11r2 progress artifacts")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write progress_board.md to the discovered output path",
    )
    parser.add_argument(
        "--write-html",
        action="store_true",
        help="Write dashboard/index.html to the discovered output path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Verify outputs are up to date (does not write). "
            "Exit 1 if outputs are missing/out-of-date; exit 2 if validation fails."
        ),
    )
    parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Run continuously and write outputs when they are missing or out of date",
    )
    parser.add_argument(
        "--update-interval",
        type=float,
        default=10.0,
        help="Polling interval in seconds for --auto-update (default: 10.0)",
    )
    parser.add_argument(
        "--html-interval",
        type=float,
        default=30.0,
        help="Auto-refresh interval in seconds for the HTML dashboard (default: 30.0)",
    )
    parser.add_argument(
        "--fail-on",
        type=_parse_fail_on,
        default=FailOn.ERROR,
        help="Exit with a non-zero status if issues >= threshold (ERROR/WARN/INFO/NEVER)",
    )

    args = parser.parse_args(argv)

    if args.check and (args.write or args.write_html or args.auto_update):
        parser.error("--check cannot be combined with --write, --write-html, or --auto-update")
    if args.update_interval <= 0:
        parser.error("--update-interval must be greater than 0")
    if args.html_interval <= 0:
        parser.error("--html-interval must be greater than 0")

    return args


def _repo_root() -> Path:
    """Return the repository root directory."""
    # scripts/docs/s11r2_progress/cli.py -> repo root
    return Path(__file__).resolve().parents[3]


def _href(from_dir: Path, to_path: Path) -> str:
    """Return a POSIX relative href from from_dir to to_path."""
    rel = Path(os.path.relpath(to_path, start=from_dir))
    return rel.as_posix()


def _format_issue(issue: Issue, *, repo_root: Path | None) -> str:
    """Format an issue for stderr output.

    Returns:
        Formatted issue string.
    """
    location = ""
    message = issue.message
    if issue.path:
        location = issue.path
        if repo_root is not None:
            try:
                location = Path(issue.path).resolve().relative_to(repo_root).as_posix()
            except ValueError:
                location = issue.path
        basename = Path(issue.path).name
        prefix = f"{basename}: "
        if message.startswith(prefix):
            message = message.removeprefix(prefix)
        if issue.line is not None:
            location = f"{location}:{issue.line}"
            if issue.column is not None:
                location = f"{location}:{issue.column}"
    if location:
        return f"{location}: {issue.severity}: {message}"
    return f"{issue.severity}: {message}"


def _merge_reports(*reports: IssueReport) -> IssueReport:
    """Merge multiple issue reports into one.

    Returns:
        Combined issue report.
    """
    merged: list[Issue] = []
    for r in reports:
        merged.extend(r.issues)
    return IssueReport(tuple(merged))


class _LogFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record, suppressing prefixes for continuation lines.

        Returns:
            Formatted log line.
        """
        if getattr(record, "continuation", False):
            return record.getMessage()
        return f"[{record.levelname}] {record.getMessage()}"


def _log_lines(lines: Iterable[str]) -> None:
    for line in lines:
        _LOGGER.info(line, extra={"continuation": True})


def _input_paths(paths: S11R2Paths) -> list[Path]:
    register_paths = sorted(paths.registers_dir.glob("*.md"))
    return [paths.registry_index, paths.status_legend, *register_paths]


def _fingerprint(paths: Iterable[Path]) -> dict[str, tuple[int, int] | None]:
    out: dict[str, tuple[int, int] | None] = {}
    for path in sorted({p.resolve() for p in paths}):
        if path.exists():
            stat = path.stat()
            out[path.as_posix()] = (stat.st_mtime_ns, stat.st_size)
        else:
            out[path.as_posix()] = None
    return out


def _diff_fingerprint(
    previous: dict[str, tuple[int, int] | None],
    current: dict[str, tuple[int, int] | None],
) -> list[str]:
    all_paths = set(previous) | set(current)
    return [path for path in sorted(all_paths) if previous.get(path) != current.get(path)]


def _format_input_path(path: str, *, base_dir: Path) -> str:
    return Path(os.path.relpath(path, start=base_dir)).as_posix()


def _format_updated_outputs(updated: list[str], *, base_dir: Path) -> str:
    names = {Path(path).name for path in updated}
    dashboard_name = Path(base_dir / "dashboard" / "index.html").name
    progress_name = Path(base_dir / "progress_board.md").name
    labels: list[str] = []
    if dashboard_name in names:
        labels.append("Dashboard")
    if progress_name in names:
        labels.append("Progress board")
    if not labels:
        labels = [Path(path).name for path in updated]
    if len(labels) == 1:
        return f"{labels[0]} updated"
    return f"{', '.join(labels[:-1])} and {labels[-1]} updated"


def _generate_outputs(
    *,
    repo_root: Path,
    fail_on: FailOn,
    allow_fail: bool,
    html_interval: float,
) -> tuple[S11R2Paths, IssueReport, str, str]:
    paths, paths_report = discover_paths(repo_root=repo_root)
    inputs_report = _guard_inputs_exist(paths)

    legend, legend_report = load_status_legend(paths.status_legend)
    metrics = compute_metrics(registers_dir=paths.registers_dir, registry_index=paths.registry_index, legend=legend)

    report = _merge_reports(paths_report, inputs_report, legend_report, metrics.report)

    if report.should_fail(fail_on=fail_on) and not allow_fail:
        raise ValueError(report)

    now = dt.datetime.now(dt.timezone.utc)
    md_out = compose_progress_board_output(paths=paths, metrics=metrics, report=report, legend=legend, now=now)

    dash_dir = paths.generated_dashboard.parent
    links = DashboardLinks(
        registry_index_href=_href(dash_dir, paths.registry_index),
        progress_board_href=_href(dash_dir, paths.generated_progress_board),
        status_legend_href=_href(dash_dir, paths.status_legend),
    )
    html_out = render_dashboard(
        metrics=metrics,
        report=report,
        links=links,
        options=DashboardRenderOptions(
            now=now,
            html_refresh_interval=html_interval,
            dashboard_dir=dash_dir,
            repo_root=repo_root,
        ),
    )

    return paths, report, md_out, html_out


def _stabilize_markdown_timestamp(existing: str, new: str) -> str:
    """Keep the existing timestamp line if only the timestamp changed.

    Returns:
        Stabilized markdown content.
    """
    patterns = (
        re.compile(r"^_Generated:\s+.*_$", flags=re.MULTILINE),
        re.compile(r"^Timestamp:\s+.*$", flags=re.MULTILINE),
    )

    for ts_re in patterns:
        existing_norm = ts_re.sub("Timestamp: __STAMP__", existing)
        new_norm = ts_re.sub("Timestamp: __STAMP__", new)

        if existing_norm != new_norm:
            continue

        m = ts_re.search(existing)
        if not m:
            continue

        return ts_re.sub(m.group(0), new, count=1)

    return new


def _stabilize_html_timestamp(existing: str, new: str) -> str:
    """Keep the existing generated timestamp if only the timestamp changed.

    Returns:
        Stabilized HTML content.
    """
    patterns = (
        re.compile(r'(<p class="sub">Generated:\s*)(.*?)(</p>)', flags=re.DOTALL),
        re.compile(r'(<div class="foot">\s*Generated at:\s*)(.*?)(\s*</div>)', flags=re.DOTALL),
    )

    for ts_re in patterns:
        existing_norm = ts_re.sub(r"\1__STAMP__\3", existing)
        new_norm = ts_re.sub(r"\1__STAMP__\3", new)

        if existing_norm != new_norm:
            continue

        m = ts_re.search(existing)
        if not m:
            continue

        old_stamp_segment = m.group(0)
        return ts_re.sub(old_stamp_segment, new, count=1)

    return new


def _is_up_to_date(path: Path, content: str, *, kind: str) -> bool:
    """Return True if the on-disk content matches content after timestamp stabilization."""
    if not path.exists():
        return False

    existing = path.read_text(encoding="utf-8")
    if kind == "md":
        stabilized = _stabilize_markdown_timestamp(existing=existing, new=content)
    elif kind == "html":
        stabilized = _stabilize_html_timestamp(existing=existing, new=content)
    # ignore JUSTIFIED: Defensive guard for unknown content kinds.
    else:  # pragma: no cover
        stabilized = content

    return stabilized == existing


def _write_text_stable(path: Path, content: str, *, kind: str) -> None:
    """Write content, attempting to keep timestamps stable if only metadata changed."""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if kind == "md":
            content = _stabilize_markdown_timestamp(existing=existing, new=content)
        elif kind == "html":
            content = _stabilize_html_timestamp(existing=existing, new=content)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _guard_inputs_exist(paths: S11R2Paths) -> IssueReport:
    issues: list[Issue] = []
    for p, label in (
        (paths.registry_index, "registry_index"),
        (paths.status_legend, "status_legend"),
    ):
        if not p.exists():
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"Missing required input file: {label} -> {p.as_posix()}",
                    path=p.as_posix(),
                )
            )
    return IssueReport(tuple(issues))


def _emit_validation_failure(report: IssueReport, *, repo_root: Path | None) -> None:
    _LOGGER.info("validation failed (%d)", len(report.issues))
    _log_lines([f"- {_format_issue(issue, repo_root=repo_root)}" for issue in report.issues])


def _try_generate(
    *,
    repo_root: Path,
    fail_on: FailOn,
    emit_errors: bool,
    allow_fail: bool,
    html_interval: float,
) -> tuple[S11R2Paths, IssueReport, str, str] | None:
    try:
        return _generate_outputs(
            repo_root=repo_root,
            fail_on=fail_on,
            allow_fail=allow_fail,
            html_interval=html_interval,
        )
    except ValueError as exc:
        report = exc.args[0] if exc.args and isinstance(exc.args[0], IssueReport) else IssueReport(())
        if emit_errors:
            _emit_validation_failure(report, repo_root=repo_root)
        return None


def _check_outputs(paths: S11R2Paths, md_out: str, html_out: str) -> int:
    missing_or_stale: list[str] = []
    if not _is_up_to_date(paths.generated_progress_board, md_out, kind="md"):
        missing_or_stale.append(paths.generated_progress_board.as_posix())
    if not _is_up_to_date(paths.generated_dashboard, html_out, kind="html"):
        missing_or_stale.append(paths.generated_dashboard.as_posix())

    if missing_or_stale:
        _LOGGER.info("outputs are missing or out of date")
        _log_lines([f"- {_format_input_path(p, base_dir=_repo_root())}" for p in missing_or_stale])
        return 1

    return 0


def _write_outputs(
    paths: S11R2Paths,
    md_out: str,
    html_out: str,
    *,
    write: bool,
    write_html: bool,
) -> list[str]:
    updated: list[str] = []
    if write and not _is_up_to_date(paths.generated_progress_board, md_out, kind="md"):
        _write_text_stable(paths.generated_progress_board, md_out, kind="md")
        updated.append(paths.generated_progress_board.as_posix())

    if write_html and not _is_up_to_date(paths.generated_dashboard, html_out, kind="html"):
        _write_text_stable(paths.generated_dashboard, html_out, kind="html")
        updated.append(paths.generated_dashboard.as_posix())

    return updated


def _auto_update(
    *,
    paths: S11R2Paths,
    md_out: str,
    html_out: str,
    write: bool,
    write_html: bool,
) -> list[str]:
    outputs_stale = not _is_up_to_date(paths.generated_progress_board, md_out, kind="md") or not _is_up_to_date(
        paths.generated_dashboard, html_out, kind="html"
    )
    if outputs_stale:
        return _write_outputs(paths, md_out, html_out, write=write, write_html=write_html)
    return []


def _issues_fingerprint(report: IssueReport) -> tuple[tuple[str, str, str | None, int | None, int | None], ...]:
    return tuple((issue.severity, issue.message, issue.path, issue.line, issue.column) for issue in report.issues)


def _run_auto_update_loop(
    *,
    repo_root: Path,
    fail_on: FailOn,
    write: bool,
    write_html: bool,
    interval: float,
    html_interval: float,
    initial_issue_fingerprint: tuple[tuple[str, str, str | None, int | None, int | None], ...] | None,
) -> int:
    last_issue_fingerprint = initial_issue_fingerprint
    last_input_fingerprint: dict[str, tuple[int, int] | None] | None = None
    _LOGGER.info("auto-update running (press Ctrl+C to stop)")
    while True:
        time.sleep(interval)
        result = _try_generate(
            repo_root=repo_root,
            fail_on=fail_on,
            emit_errors=False,
            allow_fail=True,
            html_interval=html_interval,
        )
        if result is None:
            continue
        paths, report, md_out, html_out = result
        current_inputs = _fingerprint(_input_paths(paths))
        if last_input_fingerprint is None:
            last_input_fingerprint = current_inputs
        else:
            changed_inputs = _diff_fingerprint(last_input_fingerprint, current_inputs)
            if changed_inputs:
                _LOGGER.info("inputs changed (%d)", len(changed_inputs))
                _log_lines([f"- {_format_input_path(p, base_dir=repo_root)}" for p in changed_inputs])
                last_input_fingerprint = current_inputs
                last_issue_fingerprint = None
        issue_fingerprint = _issues_fingerprint(report)
        if issue_fingerprint != last_issue_fingerprint:
            if report.issues:
                _LOGGER.info("issues detected (%d)", len(report.issues))
                _log_lines([f"- {_format_issue(issue, repo_root=repo_root)}" for issue in report.issues])
            else:
                _LOGGER.info("no issues detected")
            last_issue_fingerprint = issue_fingerprint
        updated = _auto_update(
            paths=paths,
            md_out=md_out,
            html_out=html_out,
            write=write,
            write_html=write_html,
        )
        if updated:
            _LOGGER.info(_format_updated_outputs(updated, base_dir=paths.generated_dashboard.parent))


def _apply_update_policy(
    *,
    write: bool,
    write_html: bool,
    auto_update: bool,
) -> tuple[bool, bool, bool]:
    return write, write_html, auto_update


def main(argv: list[str] | None = None) -> int:
    """Entry point for the s11r2 progress generator.

    Args:
        argv: CLI arguments (excluding the executable), or None for sys.argv.

    Returns:
        Exit code (0 for success).
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_LogFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    args = parse_args(sys.argv[1:] if argv is None else argv)

    repo_root = _repo_root()
    if args.auto_update and not (args.write or args.write_html):
        args.write = False
        args.write_html = True

    result = _try_generate(
        repo_root=repo_root,
        fail_on=args.fail_on,
        emit_errors=True,
        allow_fail=args.auto_update,
        html_interval=args.html_interval,
    )
    if result is None:
        return 2

    paths, report, md_out, html_out = result

    if args.check:
        return _check_outputs(paths, md_out, html_out)

    write, write_html, auto_update = _apply_update_policy(
        write=args.write,
        write_html=args.write_html,
        auto_update=args.auto_update,
    )

    if auto_update:
        if report.issues:
            _LOGGER.info("issues detected (%d)", len(report.issues))
            _log_lines([f"- {_format_issue(issue, repo_root=repo_root)}" for issue in report.issues])
        else:
            _LOGGER.info("no issues detected")
        updated = _auto_update(
            paths=paths,
            md_out=md_out,
            html_out=html_out,
            write=write,
            write_html=write_html,
        )
        if updated:
            _LOGGER.info(_format_updated_outputs(updated, base_dir=paths.generated_dashboard.parent))
        return _run_auto_update_loop(
            repo_root=repo_root,
            fail_on=args.fail_on,
            write=write,
            write_html=write_html,
            interval=args.update_interval,
            html_interval=args.html_interval,
            initial_issue_fingerprint=_issues_fingerprint(report),
        )

    updated = _write_outputs(paths, md_out, html_out, write=write, write_html=write_html)
    if updated:
        _LOGGER.info(_format_updated_outputs(updated, base_dir=paths.generated_dashboard.parent))

    return 0


__all__ = ["main", "parse_args"]
