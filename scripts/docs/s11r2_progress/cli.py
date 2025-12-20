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
import os
import re
import sys
from pathlib import Path

from scripts.docs.s11r2_progress.dashboard import DashboardLinks, render_dashboard
from scripts.docs.s11r2_progress.legend import load_status_legend
from scripts.docs.s11r2_progress.metrics import compute_metrics
from scripts.docs.s11r2_progress.models import FailOn, Issue, IssueReport, Severity
from scripts.docs.s11r2_progress.paths import S11R2Paths, discover_paths
from scripts.docs.s11r2_progress.render import compose_progress_board_output


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
        "--fail-on",
        type=_parse_fail_on,
        default=FailOn.ERROR,
        help="Exit with a non-zero status if issues >= threshold (ERROR/WARN/INFO/NEVER)",
    )

    args = parser.parse_args(argv)

    if args.check and (args.write or args.write_html):
        parser.error("--check cannot be combined with --write or --write-html")

    return args


def _repo_root() -> Path:
    """Return the repository root directory."""
    # scripts/docs/s11r2_progress/cli.py -> repo root
    return Path(__file__).resolve().parents[3]


def _href(from_dir: Path, to_path: Path) -> str:
    """Return a POSIX relative href from from_dir to to_path."""
    rel = Path(os.path.relpath(to_path, start=from_dir))
    return rel.as_posix()


def _format_issue(issue: Issue) -> str:
    """Format an issue for stderr output.

    Returns:
        Formatted issue string.
    """
    return f"{issue.severity}: {issue.message}"


def _merge_reports(*reports: IssueReport) -> IssueReport:
    """Merge multiple issue reports into one.

    Returns:
        Combined issue report.
    """
    merged: list[Issue] = []
    for r in reports:
        merged.extend(r.issues)
    return IssueReport(tuple(merged))


def _stabilize_markdown_timestamp(existing: str, new: str) -> str:
    """Keep the existing `_Generated:` line if only the timestamp changed.

    Returns:
        Stabilized markdown content.
    """
    ts_re = re.compile(r"^_Generated:\s+.*_$", flags=re.MULTILINE)

    existing_norm = ts_re.sub("_Generated: __STAMP__", existing)
    new_norm = ts_re.sub("_Generated: __STAMP__", new)

    if existing_norm != new_norm:
        return new

    m = ts_re.search(existing)
    if not m:
        return new

    return ts_re.sub(m.group(0), new, count=1)


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
            issues.append(Issue(Severity.ERROR, f"Missing required input file: {label} -> {p.as_posix()}"))
    return IssueReport(tuple(issues))


def main(argv: list[str] | None = None) -> int:
    """Entry point for the s11r2 progress generator.

    Args:
        argv: CLI arguments (excluding the executable), or None for sys.argv.

    Returns:
        Exit code (0 for success).
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    repo_root = _repo_root()
    paths, paths_report = discover_paths(repo_root=repo_root)
    inputs_report = _guard_inputs_exist(paths)

    legend, legend_report = load_status_legend(paths.status_legend)
    metrics = compute_metrics(registers_dir=paths.registers_dir, registry_index=paths.registry_index, legend=legend)

    report = _merge_reports(paths_report, inputs_report, legend_report, metrics.report)

    if report.should_fail(fail_on=args.fail_on):
        sys.stderr.write("s11r2-progress: validation failed\n")
        for issue in report.issues:
            sys.stderr.write(f"- {_format_issue(issue)}\n")
        return 2

    now = dt.datetime.now(dt.timezone.utc)

    md_out = compose_progress_board_output(paths=paths, metrics=metrics, report=report, legend=legend, now=now)

    dash_dir = paths.generated_dashboard.parent
    links = DashboardLinks(
        registry_index_href=_href(dash_dir, paths.registry_index),
        progress_board_href=_href(dash_dir, paths.generated_progress_board),
        status_legend_href=_href(dash_dir, paths.status_legend),
    )
    html_out = render_dashboard(legend=legend, metrics=metrics, report=report, links=links, now=now)

    if args.check:
        missing_or_stale: list[str] = []
        if not _is_up_to_date(paths.generated_progress_board, md_out, kind="md"):
            missing_or_stale.append(paths.generated_progress_board.as_posix())
        if not _is_up_to_date(paths.generated_dashboard, html_out, kind="html"):
            missing_or_stale.append(paths.generated_dashboard.as_posix())

        if missing_or_stale:
            sys.stderr.write("s11r2-progress: outputs are missing or out of date\n")
            for p in missing_or_stale:
                sys.stderr.write(f"- {p}\n")
            return 1

        return 0

    if args.write:
        _write_text_stable(paths.generated_progress_board, md_out, kind="md")

    if args.write_html:
        _write_text_stable(paths.generated_dashboard, html_out, kind="html")

    return 0


__all__ = ["main", "parse_args"]
