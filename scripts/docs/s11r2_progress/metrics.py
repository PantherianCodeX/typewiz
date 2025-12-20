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

"""Registry parsing and metric computation.

This module intentionally keeps policy assumptions minimal:

- Status codes are sourced from `STATUS_LEGEND.md` (via :class:`StatusLegend`).
- Registry discovery is driven by `registers/registry_index.md`.
- Any table column whose header contains "status" is treated as a governance
  status column and validated.

Where we do make assumptions, they are localized and easy to adjust:

- Some registries are rendered with additional derived views (e.g., rewrite
  status, master mapping ledger) to improve monitoring value.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.docs.s11r2_progress.md import (
    MdTable,
    extract_links,
    find_column,
    find_table_by_headers,
    iter_md_tables,
    render_md_table,
    strip_md_inline,
    table_rows_as_dicts,
)
from scripts.docs.s11r2_progress.metrics_helpers import (
    effective_mapping_rows,
    master_mapping_sources_context,
    master_mapping_table_context,
    rewrite_status_context,
    validate_mapping_rows,
)
from scripts.docs.s11r2_progress.models import Issue, IssueReport, Severity

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from scripts.docs.s11r2_progress.legend import StatusLegend


_YYYY_MM_DD_PARTS: int = 3


@dataclass(frozen=True, slots=True)
class MetricBlock:
    title: str
    body_md: str


@dataclass(frozen=True, slots=True)
class Metrics:
    blocks: tuple[MetricBlock, ...]
    report: IssueReport


@dataclass(frozen=True, slots=True)
class _StatusCell:
    file_label: str
    row_label: str
    status_col: str
    code: str


@dataclass(frozen=True, slots=True)
# ignore JUSTIFIED: Validation spec carries multiple related fields for error reporting.
class _StatusValidationSpec:  # pylint: disable=too-many-instance-attributes
    file_label: str
    file_path: str
    id_col: str
    status_col: str
    legend: StatusLegend
    issues: list[Issue]
    severity: Severity
    allow_empty: bool
    collected: list[_StatusCell]


def _read_text(path: Path, *, issues: list[Issue], label: str, required: bool) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if required:
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"Missing required register: {label}: {path.as_posix()}",
                    path=path.as_posix(),
                    line=1,
                )
            )
        return None


def _normalize_status(raw: str, *, legend: StatusLegend) -> str:
    return legend.normalize_code(raw)


def _count_by_status(rows: Iterable[Mapping[str, str]], status_col: str, *, legend: StatusLegend) -> Counter[str]:
    c: Counter[str] = Counter()
    for r in rows:
        code = _normalize_status(r.get(status_col, ""), legend=legend)
        if not code:
            c["(empty)"] += 1
        else:
            c[code] += 1
    return c


def _render_count_table(*, title_left: str, counts: Mapping[str, int], empty_message: str = "*No rows found.*") -> str:
    if not counts:
        return empty_message

    rows = [(k, str(v)) for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    return render_md_table([title_left, "Count"], rows, right_align={1})


def _guess_row_id_column(headers: Iterable[str]) -> str:
    # Prefer stable IDs when present.
    for frag in ("id", "artifact", "concept", "file", "source", "ovl", "term", "sup"):
        c = find_column(headers, frag)
        if c is not None:
            return c

    # Fallback: first column is usually the identifier.
    header_list = list(headers)
    return header_list[0] if header_list else "(row)"


def _validate_status_column(
    *,
    rows: Iterable[Mapping[str, str]],
    spec: _StatusValidationSpec,
    table_start_line: int,
) -> None:
    allowed = set(spec.legend.codes)

    for idx, row in enumerate(rows, start=1):
        row_id_raw = strip_md_inline(row.get(spec.id_col, "") or "").strip()
        row_id = row_id_raw or f"row {idx}"
        row_line = table_start_line + 2 + (idx - 1)

        raw_status = row.get(spec.status_col, "") or ""
        code = _normalize_status(raw_status, legend=spec.legend)

        if not code:
            if spec.allow_empty:
                continue
            spec.issues.append(
                Issue(
                    spec.severity,
                    f"{spec.file_label}: {row_id}: empty `{spec.status_col}`",
                    path=spec.file_path,
                    line=row_line,
                )
            )
            continue

        if code not in allowed:
            spec.issues.append(
                Issue(
                    spec.severity,
                    f"{spec.file_label}: {row_id}: invalid status code {code!r} in `{spec.status_col}`",
                    path=spec.file_path,
                    line=row_line,
                )
            )
            continue

        spec.collected.append(
            _StatusCell(file_label=spec.file_label, row_label=row_id, status_col=spec.status_col, code=code)
        )


def _status_columns(headers: Iterable[str]) -> list[str]:
    return [h for h in headers if "status" in h.lower()]


def _scan_registry_status_tables(
    *,
    registry_md_paths: Iterable[Path],
    registers_dir: Path,
    legend: StatusLegend,
    issues: list[Issue],
) -> tuple[Counter[str], dict[Path, Counter[str]], list[_StatusCell]]:
    overall: Counter[str] = Counter()
    per_file: dict[Path, Counter[str]] = {}
    cells: list[_StatusCell] = []

    for p in sorted({rp.resolve() for rp in registry_md_paths}):
        if p.name == "registry_index.md":
            continue

        txt = _read_text(p, issues=issues, label=p.name, required=True)
        if txt is None:
            continue

        file_label = p.relative_to(registers_dir).as_posix() if p.is_relative_to(registers_dir) else p.as_posix()
        file_counter: Counter[str] = Counter()
        has_status_cols = False

        for t in iter_md_tables(txt):
            status_cols = _status_columns(t.header)
            if not status_cols:
                continue

            has_status_cols = True

            id_col = _guess_row_id_column(t.header)
            rows = table_rows_as_dicts(t)

            for status_col in status_cols:
                collected_cells: list[_StatusCell] = []
                _validate_status_column(
                    rows=rows,
                    spec=_StatusValidationSpec(
                        file_label=file_label,
                        file_path=p.as_posix(),
                        id_col=id_col,
                        status_col=status_col,
                        legend=legend,
                        issues=issues,
                        severity=Severity.ERROR,
                        allow_empty=False,
                        collected=collected_cells,
                    ),
                    table_start_line=t.start_line,
                )

                for c in collected_cells:
                    cells.append(c)
                    file_counter[c.code] += 1
                    overall[c.code] += 1

        if has_status_cols:
            per_file[p] = file_counter

    return overall, per_file, cells


def _render_per_registry_distribution(
    *,
    per_file: Mapping[Path, Counter[str]],
    legend: StatusLegend,
    registers_dir: Path,
) -> str:
    codes = list(legend.codes)
    headers = ["Registry", "Total", *codes]

    rows: list[list[str]] = []
    for p, c in sorted(per_file.items(), key=lambda kv: kv[0].name):
        label = p.relative_to(registers_dir).as_posix() if p.is_relative_to(registers_dir) else p.as_posix()
        total = sum(c.values())
        row: list[str] = [f"`{label}`", str(total)]
        row.extend(str(c.get(code, 0)) for code in codes)
        rows.append(row)

    right_align = set(range(1, len(headers)))
    return render_md_table(headers, rows, right_align=right_align)


def _render_overall_distribution(*, overall: Counter[str]) -> str:
    return _render_count_table(
        title_left="Status",
        counts=overall,
        empty_message="*No status-bearing rows found.*",
    )


def _discover_registry_md_paths(
    *, registry_index: Path, registers_dir: Path, issues: list[Issue]
) -> tuple[set[Path], set[Path]]:
    """Return (indexed_md_under_registers, present_md_under_registers)."""
    index_txt = _read_text(registry_index, issues=issues, label="registry_index.md", required=True)
    if index_txt is None:
        return set(), set()

    index_dir = registry_index.parent
    links = extract_links(index_txt)

    indexed: set[Path] = set()
    for _text, target in links:
        tp = (index_dir / Path(target)).resolve()
        if tp.suffix.lower() == ".md" and tp.is_relative_to(registers_dir):
            if not tp.exists():
                issues.append(
                    Issue(
                        Severity.ERROR,
                        f"registry_index.md: linked registry missing: {target}",
                        path=registry_index.as_posix(),
                        line=1,
                    )
                )
            indexed.add(tp)

    present = {p.resolve() for p in registers_dir.rglob("*.md") if p.is_file()}
    present.discard(registry_index.resolve())

    # Warn about registries that exist but are not indexed (drift / discoverability issue).
    unindexed = sorted(present - indexed)
    for p in unindexed:
        rel = p.relative_to(registers_dir).as_posix() if p.is_relative_to(registers_dir) else p.as_posix()
        issues.append(
            Issue(
                Severity.WARN,
                f"registry_index.md: registry present but not indexed: {rel}",
                path=registry_index.as_posix(),
                line=1,
            )
        )

    return indexed, present


def _top_rows_with_code(
    *,
    cells: Iterable[_StatusCell],
    want_code: str,
    limit: int,
) -> list[_StatusCell]:
    out: list[_StatusCell] = [c for c in cells if c.code == want_code]
    # stable and readable: by file then row label
    out.sort(key=lambda c: (c.file_label, c.row_label))
    return out[:limit]


def _render_top_blockers(*, blockers: list[_StatusCell]) -> str:
    if not blockers:
        return "*No blocked rows found.*"

    headers = ["Registry", "Row", "Status column"]
    rows = [(f"`{b.file_label}`", b.row_label, b.status_col) for b in blockers]
    return render_md_table(headers, rows)


def _render_outstanding_table(
    *,
    title: str,
    rows: Iterable[Mapping[str, str]],
    columns: list[str],
    legend: StatusLegend,
    status_col: str,
    done_code: str | None,
    limit: int,
) -> MetricBlock:
    if done_code is None:
        done_code = "DN" if "DN" in legend.codes else None

    out_rows: list[list[str]] = []
    for r in rows:
        code = _normalize_status(r.get(status_col, ""), legend=legend)
        if done_code is not None and code == done_code:
            continue
        out_rows.append([strip_md_inline(r.get(c, "") or "").strip() for c in columns])

    body = "*No outstanding items.*" if not out_rows else render_md_table(columns, out_rows[:limit])
    return MetricBlock(title=title, body_md=body)


def _rewrite_staleness_block(
    *,
    rows: Sequence[Mapping[str, str]],
    table: MdTable,
    legend: StatusLegend,
    status_col: str,
    done_code: str | None,
    issues: list[Issue],
) -> MetricBlock:
    last_touch_col = find_column(table.header, "last") or "Last touch (YYYY-MM-DD)"
    active_codes = {
        legend.code_for_label_prefix("in progress"),
        legend.code_for_label_prefix("review"),
        legend.code_for_label_prefix("blocked"),
    }
    active_codes = {c for c in active_codes if c is not None}

    stale_rows: list[tuple[int, list[str]]] = []
    today = dt.datetime.now(dt.timezone.utc).date()
    for row in rows:
        code = _normalize_status(row.get(status_col, ""), legend=legend)
        if done_code is not None and code == done_code:
            continue

        last_raw = strip_md_inline(row.get(last_touch_col, "") or "").strip()
        last = _parse_yyyy_mm_dd(last_raw)

        if code in active_codes and not last_raw:
            artifact = strip_md_inline(row.get(find_column(table.header, "artifact") or "Artifact", "") or "").strip()
            issues.append(
                Issue(
                    Severity.WARN,
                    f"rewrite_status.md: {artifact or '(row)'}: missing Last touch for active status {code!r}",
                )
            )

        if last is None:
            continue

        age = (today - last).days
        artifact = strip_md_inline(row.get(find_column(table.header, "artifact") or "Artifact", "") or "").strip()
        next_action = strip_md_inline(row.get(find_column(table.header, "next") or "Next action", "") or "").strip()
        stale_rows.append((age, [artifact, code or "", last.isoformat(), str(age), next_action]))

    stale_rows.sort(key=lambda x: (-x[0], x[1][0]))
    if stale_rows:
        stale_table = render_md_table(
            ["Artifact", "Status", "Last touch", "Age (days)", "Next action"],
            [row for _age, row in stale_rows[:15]],
            right_align={3},
        )
    else:
        stale_table = "*No dated outstanding items found.*"

    return MetricBlock(title="Rewrite status: staleness (dated outstanding)", body_md=stale_table)


def _parse_yyyy_mm_dd(raw: str) -> dt.date | None:
    s = raw.strip()
    if not s:
        return None
    try:
        parts = s.split("-")
        if len(parts) != _YYYY_MM_DD_PARTS:
            return None
        y, m, d = (int(parts[0]), int(parts[1]), int(parts[2]))
        return dt.date(y, m, d)
    except ValueError:
        return None


def _table_counts(
    path: Path,
    header_frags: list[str],
    *,
    legend: StatusLegend,
    done_code: str | None,
) -> tuple[int, int, int]:
    try:
        txt = path.read_text(encoding="utf-8")
    except OSError:
        return (0, 0, 0)

    table = find_table_by_headers(txt, header_frags)
    if table is None:
        return (0, 0, 0)

    rows = table_rows_as_dicts(table)
    status_col = find_column(table.header, "status") or "Status"

    total = 0
    done = 0
    for row in rows:
        code = _normalize_status(row.get(status_col, ""), legend=legend)
        if not code:
            continue
        total += 1
        if done_code is not None and code == done_code:
            done += 1
    return (total, done, max(total - done, 0))


def _count_open_questions_blocking(
    *,
    registers_dir: Path,
    legend: StatusLegend,
    done_code: str | None,
) -> int:
    try:
        oq_txt = (registers_dir / "open_questions.md").read_text(encoding="utf-8")
    except OSError:
        return 0

    oq_t = find_table_by_headers(oq_txt, ["q id", "status"])
    if oq_t is None:
        return 0

    oq_rows = table_rows_as_dicts(oq_t)
    oq_status_col = find_column(oq_t.header, "status") or "Status"
    blocking_col = find_column(oq_t.header, "blocking") or "Blocking? (yes/no)"
    blocking_yes = 0
    for row in oq_rows:
        code = _normalize_status(row.get(oq_status_col, ""), legend=legend)
        if done_code is not None and code == done_code:
            continue
        v = strip_md_inline(row.get(blocking_col, "") or "").strip().lower()
        if v == "yes":
            blocking_yes += 1
    return blocking_yes


def _draft2_mapping_coverage(*, registers_dir: Path) -> tuple[int, int]:
    try:
        mm_txt = (registers_dir / "master_mapping_ledger.md").read_text(encoding="utf-8")
    except OSError:
        return (0, 0)

    src_t = find_table_by_headers(mm_txt, ["source id", "file", "status"])
    map_t = (
        find_table_by_headers(mm_txt, ["row id", "source id", "destination", "status"])
        or find_table_by_headers(mm_txt, ["map id", "source id", "target", "status"])
        or find_table_by_headers(mm_txt, ["row id", "source id", "target", "status"])
    )

    d2_ids: list[str] = []
    if src_t is not None:
        src_rows = table_rows_as_dicts(src_t)
        sid_col = find_column(src_t.header, "source id") or "Source ID"
        d2_ids = [strip_md_inline(r.get(sid_col, "") or "").strip() for r in src_rows]
        d2_ids = [sid for sid in d2_ids if sid.startswith("D2-")]

    if map_t is None or not d2_ids:
        return (0, len(d2_ids))

    map_rows = table_rows_as_dicts(map_t)
    src_col = find_column(map_t.header, "source id") or "Source ID"
    dest_col = find_column(map_t.header, "destination") or find_column(map_t.header, "target") or "Destination doc"

    mapped: set[str] = set()
    for row in map_rows:
        sid = strip_md_inline(row.get(src_col, "") or "").strip()
        dest = strip_md_inline(row.get(dest_col, "") or "").strip()
        if not sid and not dest:
            continue
        if sid:
            mapped.add(sid)

    return (sum(1 for sid in d2_ids if sid in mapped), len(d2_ids))


def _metrics_operational_snapshot(
    *,
    registers_dir: Path,
    legend: StatusLegend,
    indexed_md: int,
    present_md: int,
    registries_with_status_columns: int,
    registries_with_status_rows: int,
    overall: Counter[str],
) -> MetricBlock:
    """Return a KPI snapshot suitable for a monitoring view.

    Best-effort by design: failures here should not block progress generation.
    """
    done_code = legend.code_for_label_prefix("done") or ("DN" if "DN" in legend.codes else None)
    blocked_code = legend.code_for_label_prefix("blocked")

    total_status_rows = sum(overall.values())
    done_rows = overall.get(done_code, 0) if done_code is not None else 0
    pct_done = (done_rows / total_status_rows * 100.0) if total_status_rows else 0.0

    blocked_rows = overall.get(blocked_code, 0) if blocked_code is not None else 0

    rewrite_counts = _table_counts(
        registers_dir / "rewrite_status.md",
        ["artifact", "status"],
        legend=legend,
        done_code=done_code,
    )
    oq_counts = _table_counts(
        registers_dir / "open_questions.md",
        ["q id", "status"],
        legend=legend,
        done_code=done_code,
    )
    blocking_yes = _count_open_questions_blocking(registers_dir=registers_dir, legend=legend, done_code=done_code)
    d2_sources_with_mapping, d2_sources_total = _draft2_mapping_coverage(registers_dir=registers_dir)

    headers = ["Metric", "Value"]
    rows = [
        ["Indexed registries (markdown)", str(indexed_md)],
        ["Registries present on disk (markdown)", str(present_md)],
        ["Registries with status columns", str(registries_with_status_columns)],
        ["Registries with status-bearing rows", str(registries_with_status_rows)],
        ["Status-bearing rows", str(total_status_rows)],
        ["Done rows", f"{done_rows} ({pct_done:.1f}%)"],
        ["Blocked rows", str(blocked_rows)],
        [
            "Rewrite artifacts (total / done / outstanding)",
            f"{rewrite_counts[0]} / {rewrite_counts[1]} / {rewrite_counts[2]}",
        ],
        ["Open questions (total / done / outstanding)", f"{oq_counts[0]} / {oq_counts[1]} / {oq_counts[2]}"],
        ["Open questions blocking=yes (outstanding)", str(blocking_yes)],
        ["Draft-2 sources with mapping rows", f"{d2_sources_with_mapping} / {d2_sources_total}"],
    ]

    return MetricBlock(title="Operational snapshot", body_md=render_md_table(headers, rows, right_align={1}))


def _summary_block(*, overall: Counter[str], legend: StatusLegend) -> MetricBlock:
    """Render a summary block with totals and distribution.

    Returns:
        Summary metric block.
    """
    done_code = legend.code_for_label_prefix("done") or ("DN" if "DN" in legend.codes else None)
    done_count = overall.get(done_code, 0) if done_code is not None else 0
    total_count = sum(overall.values())
    pct_done = (done_count / total_count * 100.0) if total_count else 0.0

    summary_lines: list[str] = [
        f"- Status-bearing rows: {total_count}",
    ]
    if done_code is not None:
        summary_lines.append(f"- Done ({done_code}): {done_count} ({pct_done:.1f}%)")

    return MetricBlock(
        title="Summary",
        body_md="\n".join(summary_lines) + "\n\n" + _render_overall_distribution(overall=overall),
    )


def _metrics_for_rewrite_status(*, registers_dir: Path, legend: StatusLegend, issues: list[Issue]) -> list[MetricBlock]:
    path = registers_dir / "rewrite_status.md"
    txt = _read_text(path, issues=issues, label=path.name, required=True)
    if txt is None:
        return []

    context = rewrite_status_context(txt=txt, path=path, legend=legend, issues=issues)
    if context is None:
        return []

    counts = _count_by_status(context.rows, context.status_col, legend=legend)
    dist = MetricBlock(
        title="Rewrite status: distribution",
        body_md=_render_count_table(title_left="Status", counts=counts),
    )

    columns = [
        context.artifact_col,
        context.status_col,
        context.owner_col,
        context.next_col,
    ]
    outstanding = _render_outstanding_table(
        title="Rewrite status: outstanding",
        rows=context.rows,
        columns=columns,
        legend=legend,
        status_col=context.status_col,
        done_code=context.done_code,
        limit=30,
    )

    # Next actions: compact table with the most actionable columns.
    next_cols = [context.artifact_col, context.status_col, context.next_col]
    next_actions = _render_outstanding_table(
        title="Rewrite status: next actions",
        rows=context.rows,
        columns=next_cols,
        legend=legend,
        status_col=context.status_col,
        done_code=context.done_code,
        limit=30,
    )
    staleness = _rewrite_staleness_block(
        rows=context.rows,
        table=context.table,
        legend=legend,
        status_col=context.status_col,
        done_code=context.done_code,
        issues=issues,
    )

    return [dist, outstanding, next_actions, staleness]


def _metrics_for_open_questions(*, registers_dir: Path, legend: StatusLegend, issues: list[Issue]) -> list[MetricBlock]:
    path = registers_dir / "open_questions.md"
    txt = _read_text(path, issues=issues, label=path.name, required=True)
    if txt is None:
        return []

    t = find_table_by_headers(txt, ["q id", "status"])
    if t is None:
        issues.append(Issue(Severity.ERROR, "open_questions.md: expected a table with Q ID and Status columns"))
        return []

    rows = table_rows_as_dicts(t)
    status_col = find_column(t.header, "status") or "Status"

    counts = _count_by_status(rows, status_col, legend=legend)
    dist = MetricBlock(
        title="Open questions: distribution",
        body_md=_render_count_table(title_left="Status", counts=counts),
    )

    done_code = legend.code_for_label_prefix("done")
    columns = [
        find_column(t.header, "q id") or "Q ID",
        find_column(t.header, "blocking") or "Blocking? (yes/no)",
        find_column(t.header, "impacted") or "Impacted docs",
        status_col,
    ]
    outstanding = _render_outstanding_table(
        title="Open questions: outstanding",
        rows=rows,
        columns=columns,
        legend=legend,
        status_col=status_col,
        done_code=done_code,
        limit=25,
    )

    return [dist, outstanding]


def _metrics_for_master_mapping(*, registers_dir: Path, legend: StatusLegend, issues: list[Issue]) -> list[MetricBlock]:
    path = registers_dir / "master_mapping_ledger.md"
    txt = _read_text(path, issues=issues, label=path.name, required=True)
    if txt is None:
        return []

    blocks: list[MetricBlock] = []

    source_ctx = master_mapping_sources_context(txt=txt, path=path, issues=issues)
    if source_ctx is None:
        return []

    src_counts = _count_by_status(source_ctx.rows, source_ctx.status_col, legend=legend)
    blocks.append(
        MetricBlock(
            title="Sources: status distribution",
            body_md=_render_count_table(title_left="Status", counts=src_counts),
        )
    )

    mapping_ctx = master_mapping_table_context(txt=txt, path=path, issues=issues)
    if mapping_ctx is None:
        return blocks

    # Ignore placeholder mapping rows where Source ID and destination are both empty.
    effective_map_rows, placeholder = effective_mapping_rows(
        rows=mapping_ctx.rows_with_lines,
        source_col=mapping_ctx.source_col,
        dest_col=mapping_ctx.dest_col,
    )

    if placeholder:
        issues.append(
            Issue(
                Severity.INFO,
                f"master_mapping_ledger.md: ignored {placeholder} placeholder "
                f"mapping row(s) (empty Source ID and Destination doc)",
            )
        )

    per_source_map_rows = validate_mapping_rows(
        rows=effective_map_rows,
        source_col=mapping_ctx.source_col,
        dest_col=mapping_ctx.dest_col,
        known_sources=source_ctx.known_sources,
        path=path,
        issues=issues,
    )

    map_counts = _count_by_status(
        [row for _line, row in effective_map_rows],
        mapping_ctx.status_col,
        legend=legend,
    )
    blocks.append(
        MetricBlock(
            title="Mapping rows: status distribution",
            body_md=_render_count_table(
                title_left="Status",
                counts=map_counts,
                empty_message="*No effective mapping rows found.*",
            ),
        )
    )

    # Per-source mapping coverage.
    inv_headers = ["Source ID", "File", "Status", "Mapping rows"]
    inv_rows: list[list[str]] = []
    for r in source_ctx.rows:
        sid = strip_md_inline(r.get(source_ctx.id_col, "") or "").strip()
        if not sid:
            continue
        inv_rows.append([
            sid,
            (r.get(source_ctx.file_col, "") or "").strip(),
            _normalize_status(r.get(source_ctx.status_col, ""), legend=legend) or "",
            str(per_source_map_rows.get(sid, 0)),
        ])

    blocks.append(
        MetricBlock(
            title="Sources: inventory",
            body_md=render_md_table(inv_headers, inv_rows, right_align={3}),
        )
    )

    # If we have any mapping, highlight which sources still have none.
    if effective_map_rows:
        missing = sorted(s for s in source_ctx.known_sources if not per_source_map_rows.get(s, 0))
        if missing:
            blocks.append(
                MetricBlock(
                    title="Sources with zero mapping rows",
                    body_md="\n".join(["- " + s for s in missing[:25]]),
                )
            )
    else:
        sources = sorted(source_ctx.known_sources)
        if sources:
            blocks.append(
                MetricBlock(
                    title="Mapping coverage",
                    body_md=f"- Effective mapping rows: 0\n- Sources: {len(sources)}\n- Sources with mapping rows: 0",
                )
            )

    return blocks


def compute_metrics(
    registers_dir: Path,
    *,
    registry_index: Path,
    legend: StatusLegend,
) -> Metrics:
    """Compute metrics and issue reports for s11r2 registries.

    Args:
        registers_dir: Directory containing registry markdown files.
        registry_index: Path to registry_index.md.
        legend: Status legend for validation.

    Returns:
        Aggregated metrics and issue report.
    """
    issues: list[Issue] = []

    indexed_md, present_md = _discover_registry_md_paths(
        registry_index=registry_index, registers_dir=registers_dir, issues=issues
    )

    overall, per_file, cells = _scan_registry_status_tables(
        registry_md_paths=present_md,
        registers_dir=registers_dir,
        legend=legend,
        issues=issues,
    )

    blocks: list[MetricBlock] = []

    blocks.extend([
        _metrics_operational_snapshot(
            registers_dir=registers_dir,
            legend=legend,
            indexed_md=len(indexed_md),
            present_md=len(present_md),
            registries_with_status_columns=len(per_file),
            registries_with_status_rows=sum(1 for c in per_file.values() if sum(c.values()) > 0),
            overall=overall,
        ),
        _summary_block(overall=overall, legend=legend),
    ])

    if per_file:
        blocks.append(
            MetricBlock(
                title="Per-registry status distribution",
                body_md=_render_per_registry_distribution(
                    per_file=per_file, legend=legend, registers_dir=registers_dir
                ),
            )
        )

    blocked_code = legend.code_for_label_prefix("blocked")
    if blocked_code is not None:
        blockers = _top_rows_with_code(cells=cells, want_code=blocked_code, limit=25)
        blocks.append(MetricBlock(title="Top blocked rows", body_md=_render_top_blockers(blockers=blockers)))

    # Detailed, high-value tables
    blocks.extend(_metrics_for_open_questions(registers_dir=registers_dir, legend=legend, issues=issues))
    blocks.extend(_metrics_for_rewrite_status(registers_dir=registers_dir, legend=legend, issues=issues))
    blocks.extend(_metrics_for_master_mapping(registers_dir=registers_dir, legend=legend, issues=issues))

    # Coverage clarity (what's indexed vs present)
    unindexed_present = sorted((present_md - indexed_md) - {registry_index.resolve()})
    if unindexed_present:
        body = "\n".join(["- `" + p.relative_to(registers_dir).as_posix() + "`" for p in unindexed_present])
    else:
        body = "*No unindexed registry markdown files found.*"

    blocks.append(MetricBlock(title="Registry coverage", body_md=body))

    return Metrics(blocks=tuple(blocks), report=IssueReport(tuple(issues)))


__all__ = ["MetricBlock", "Metrics", "compute_metrics"]
