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

"""Status legend parsing.

The status legend is the single source of truth for governance status codes.

The generator reads `STATUS_LEGEND.md` to:
- validate status codes used in registries;
- render a consistent legend into generated outputs.

Status codes are normalized by:
- stripping simple inline Markdown wrappers (e.g., **NS**, `NS`);
- trimming whitespace;
- extracting a leading token when additional annotations are present
  (e.g., `NS (prep)` -> `NS`);
- upper-casing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from scripts.docs.s11r2_progress.md import find_column, find_table_by_headers, strip_md_inline, table_rows_with_lines
from scripts.docs.s11r2_progress.models import Issue, IssueReport, Severity

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

_CODE_TOKEN_RE = re.compile(r"^(?P<code>[A-Za-z0-9][A-Za-z0-9_-]{0,15})\b")


def _empty_str_mapping() -> dict[str, str]:
    return {}


@dataclass(frozen=True, slots=True)
class StatusLegend:
    """Parsed status legend with lookup helpers."""

    codes: tuple[str, ...]
    labels_by_code: Mapping[str, str]
    meanings_by_code: Mapping[str, str] = field(default_factory=_empty_str_mapping)

    @staticmethod
    def normalize_code(raw: str) -> str:
        """Normalize an arbitrary cell value into a canonical status code.

        This is intentionally tolerant of minor annotations in registries while
        still enforcing that the *code itself* is drawn from the legend.

        Args:
            raw: Raw status cell value.

        Returns:
            Normalized status code (uppercase) or "" if empty.
        """
        s = strip_md_inline(raw or "").strip()
        if not s:
            return ""

        m = _CODE_TOKEN_RE.match(s)
        if m:
            return m.group("code").strip().upper()

        return s.upper()

    def is_valid_code(self, raw: str) -> bool:
        """Return True if the raw value maps to a known status code.

        Args:
            raw: Raw status cell value.

        Returns:
            True if the normalized code is in the legend.
        """
        code = self.normalize_code(raw)
        return bool(code) and code in self.labels_by_code

    def label_for(self, code: str) -> str:
        """Return the label for a status code.

        Args:
            code: Status code to look up.

        Returns:
            Human-readable status label.
        """
        return self.labels_by_code.get(code.strip().upper(), "")

    def meaning_for(self, code: str) -> str:
        """Return the meaning for a status code.

        Args:
            code: Status code to look up.

        Returns:
            Status meaning text.
        """
        return self.meanings_by_code.get(code.strip().upper(), "")

    def code_for_label(self, label: str) -> str | None:
        """Return the first code whose label exactly matches `label` (case-insensitive).

        Args:
            label: Label text to match.

        Returns:
            Matching status code, or None if not found.
        """
        want = label.strip().lower()
        for c in self.codes:
            if self.labels_by_code.get(c, "").strip().lower() == want:
                return c
        return None

    def code_for_label_prefix(self, prefix: str) -> str | None:
        """Return the first code whose label starts with `prefix` (case-insensitive).

        Args:
            prefix: Label prefix to match.

        Returns:
            Matching status code, or None if not found.
        """
        want = prefix.strip().lower()
        for c in self.codes:
            if self.labels_by_code.get(c, "").strip().lower().startswith(want):
                return c
        return None


def _collect_legend_entries(
    *,
    rows: Sequence[tuple[int, Mapping[str, str]]],
    code_col: str,
    label_col: str,
    meaning_col: str | None,
    path: Path,
    issues: list[Issue],
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Collect unique legend entries from table rows.

    Args:
        rows: Parsed table rows.
        code_col: Column name for codes.
        label_col: Column name for labels.
        meaning_col: Optional column name for meanings.
        path: Path to the file.
        issues: Issue list to append warnings to.

    Returns:
        Tuple of codes list, labels map, and meanings map.
    """
    codes: list[str] = []
    labels: dict[str, str] = {}
    meanings: dict[str, str] = {}

    for line_no, row in rows:
        code_raw = row.get(code_col, "")
        label_raw = row.get(label_col, "")
        meaning_raw = row.get(meaning_col, "") if meaning_col else ""

        code = strip_md_inline(code_raw).strip().upper()
        label = strip_md_inline(label_raw).strip()
        meaning = strip_md_inline(meaning_raw).strip()

        if not code:
            continue

        if code in labels:
            if labels[code] != label:
                msg = (
                    f"STATUS_LEGEND.md: duplicate code {code!r} with different labels "
                    f"({labels[code]!r} vs {label!r}); using first"
                )
                issues.append(Issue(Severity.WARN, msg, path=path.as_posix(), line=line_no))
            continue

        codes.append(code)
        labels[code] = label
        if meaning:
            meanings[code] = meaning

    return codes, labels, meanings


def load_status_legend(path: Path) -> tuple[StatusLegend, IssueReport]:
    """Load the status legend and return it with any issues.

    Args:
        path: Path to STATUS_LEGEND.md.

    Returns:
        Parsed status legend and issue report.
    """
    issues: list[Issue] = []

    if not path.exists():
        issues.append(Issue(Severity.ERROR, f"STATUS_LEGEND.md: missing: {path.as_posix()}", path=path.as_posix()))
        return StatusLegend((), {}), IssueReport(tuple(issues))

    text = path.read_text(encoding="utf-8")
    table = find_table_by_headers(text, ["code", "label"])
    if table is None:
        issues.append(
            Issue(
                Severity.ERROR,
                'STATUS_LEGEND.md: could not locate a table with "Code" and "Label" headers',
                path=path.as_posix(),
                line=1,
            )
        )
        return StatusLegend((), {}), IssueReport(tuple(issues))

    code_col = find_column(table.header, "code")
    label_col = find_column(table.header, "label")
    meaning_col = find_column(table.header, "meaning")

    if code_col is None or label_col is None:
        issues.append(
            Issue(
                Severity.ERROR,
                "STATUS_LEGEND.md: table found, but could not resolve Code/Label columns",
                path=path.as_posix(),
                line=table.start_line,
            )
        )
        return StatusLegend((), {}), IssueReport(tuple(issues))

    rows = table_rows_with_lines(table)
    codes, labels, meanings = _collect_legend_entries(
        rows=rows,
        code_col=code_col,
        label_col=label_col,
        meaning_col=meaning_col,
        path=path,
        issues=issues,
    )

    if not codes:
        issues.append(
            Issue(
                Severity.ERROR,
                "STATUS_LEGEND.md: no status codes found",
                path=path.as_posix(),
                line=table.start_line,
            )
        )

    return StatusLegend(tuple(codes), labels, meanings), IssueReport(tuple(issues))


__all__ = ["StatusLegend", "load_status_legend"]
