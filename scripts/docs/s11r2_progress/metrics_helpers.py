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

"""Helper structures for s11r2 progress metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.docs.s11r2_progress.md import find_column, find_table_by_headers, strip_md_inline, table_rows_as_dicts
from scripts.docs.s11r2_progress.models import Issue, Severity

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from scripts.docs.s11r2_progress.legend import StatusLegend
    from scripts.docs.s11r2_progress.md import MdTable


@dataclass(frozen=True, slots=True)
class RewriteStatusContext:
    table: MdTable
    rows: Sequence[Mapping[str, str]]
    status_col: str
    done_code: str | None
    artifact_col: str
    owner_col: str
    next_col: str
    last_touch_col: str


@dataclass(frozen=True, slots=True)
class MasterMappingSourceContext:
    table: MdTable
    rows: Sequence[Mapping[str, str]]
    id_col: str
    file_col: str
    status_col: str
    known_sources: set[str]


@dataclass(frozen=True, slots=True)
class MasterMappingTableContext:
    table: MdTable
    rows: Sequence[Mapping[str, str]]
    status_col: str
    source_col: str
    dest_col: str


def rewrite_status_context(
    *,
    txt: str,
    legend: StatusLegend,
    issues: list[Issue],
) -> RewriteStatusContext | None:
    """Parse the rewrite status table into a reusable context.

    Args:
        txt: Full rewrite_status.md content.
        legend: Status legend for normalization.
        issues: Issue list to append errors to.

    Returns:
        Parsed context, or None if the table is missing.
    """
    table = find_table_by_headers(txt, ["artifact", "status"])
    if table is None:
        issues.append(Issue(Severity.ERROR, "rewrite_status.md: expected a table with Artifact and Status columns"))
        return None

    rows = table_rows_as_dicts(table)
    status_col = find_column(table.header, "status") or "Status"
    done_code = legend.code_for_label_prefix("done")

    return RewriteStatusContext(
        table=table,
        rows=rows,
        status_col=status_col,
        done_code=done_code,
        artifact_col=find_column(table.header, "artifact") or "Artifact",
        owner_col=find_column(table.header, "owner") or "Owner",
        next_col=find_column(table.header, "next") or "Next action",
        last_touch_col=find_column(table.header, "last") or "Last touch (YYYY-MM-DD)",
    )


def master_mapping_sources_context(
    *,
    txt: str,
    issues: list[Issue],
) -> MasterMappingSourceContext | None:
    """Parse the sources table for the master mapping ledger.

    Args:
        txt: Full master_mapping_ledger.md content.
        issues: Issue list to append errors to.

    Returns:
        Parsed source context, or None if the table is missing.
    """
    sources_t = find_table_by_headers(txt, ["source id", "file", "status"])
    if sources_t is None:
        issues.append(
            Issue(Severity.ERROR, "master_mapping_ledger.md: expected a table with Source ID / File / Status")
        )
        return None

    src_rows = table_rows_as_dicts(sources_t)
    src_id_col = find_column(sources_t.header, "source id") or "Source ID"
    src_file_col = find_column(sources_t.header, "file") or "File"
    src_status_col = find_column(sources_t.header, "status") or "Status"

    known_sources = {
        strip_md_inline(r.get(src_id_col, "") or "").strip() for r in src_rows if (r.get(src_id_col, "") or "").strip()
    }

    return MasterMappingSourceContext(
        table=sources_t,
        rows=src_rows,
        id_col=src_id_col,
        file_col=src_file_col,
        status_col=src_status_col,
        known_sources=known_sources,
    )


def master_mapping_table_context(*, txt: str, issues: list[Issue]) -> MasterMappingTableContext | None:
    """Locate and parse the master mapping table, if present.

    Args:
        txt: Full master_mapping_ledger.md content.
        issues: Issue list to append warnings to.

    Returns:
        Parsed mapping context, or None if the table is missing.
    """
    mapping_t: MdTable | None = None
    for header_frags in (
        ["map id", "source id", "target", "status"],
        ["row id", "source id", "destination", "status"],
        ["row id", "source id", "target", "status"],
    ):
        mapping_t = find_table_by_headers(txt, header_frags)
        if mapping_t is not None:
            break

    if mapping_t is None:
        issues.append(
            Issue(
                Severity.WARN,
                (
                    "master_mapping_ledger.md: mapping table not found (expected headers similar to: "
                    "MAP ID / Source ID / Target / Status or Row ID / Source ID / Destination doc / Status)"
                ),
            )
        )
        return None

    map_rows = table_rows_as_dicts(mapping_t)
    map_status_col = find_column(mapping_t.header, "status") or "Status"
    map_src_col = find_column(mapping_t.header, "source id") or "Source ID"
    map_dest_col = (
        find_column(mapping_t.header, "destination") or find_column(mapping_t.header, "target") or "Destination doc"
    )

    return MasterMappingTableContext(
        table=mapping_t,
        rows=map_rows,
        status_col=map_status_col,
        source_col=map_src_col,
        dest_col=map_dest_col,
    )


def effective_mapping_rows(
    *,
    rows: Sequence[Mapping[str, str]],
    source_col: str,
    dest_col: str,
) -> tuple[list[Mapping[str, str]], int]:
    """Filter out placeholder mapping rows and return effective rows + count.

    Args:
        rows: Mapping table rows.
        source_col: Source ID column name.
        dest_col: Destination column name.

    Returns:
        Tuple of effective rows and placeholder row count.
    """
    effective_rows: list[Mapping[str, str]] = []
    placeholder = 0
    for row in rows:
        sid = strip_md_inline(row.get(source_col, "") or "").strip()
        dest = strip_md_inline(row.get(dest_col, "") or "").strip()
        if not sid and not dest:
            placeholder += 1
            continue
        effective_rows.append(row)

    return (effective_rows, placeholder)


def validate_mapping_rows(
    *,
    rows: Sequence[Mapping[str, str]],
    source_col: str,
    dest_col: str,
    known_sources: set[str],
    issues: list[Issue],
) -> Counter[str]:
    """Validate mapping rows and return a per-source row count.

    Args:
        rows: Effective mapping rows.
        source_col: Source ID column name.
        dest_col: Destination column name.
        known_sources: Known source IDs for validation.
        issues: Issue list to append errors and warnings to.

    Returns:
        Counter of mapping rows per source id.
    """
    referenced_sources: set[str] = set()
    per_source_map_rows: Counter[str] = Counter()

    for row in rows:
        sid = strip_md_inline(row.get(source_col, "") or "").strip()
        dest = strip_md_inline(row.get(dest_col, "") or "").strip()
        if sid:
            referenced_sources.add(sid)
            per_source_map_rows[sid] += 1
        if not sid:
            issues.append(Issue(Severity.WARN, "master_mapping_ledger.md: mapping row missing Source ID"))
        if not dest:
            issues.append(Issue(Severity.WARN, "master_mapping_ledger.md: mapping row missing Destination doc"))

    unknown_refs = sorted(referenced_sources - known_sources)
    issues.extend(
        Issue(Severity.ERROR, f"master_mapping_ledger.md: mapping references unknown Source ID: {sid}")
        for sid in unknown_refs
    )

    return per_source_map_rows
