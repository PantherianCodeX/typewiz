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

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Mapping

from scripts.docs.s11r2_progress.md import find_column, find_table_by_headers, strip_md_inline, table_rows_as_dicts
from scripts.docs.s11r2_progress.models import Issue, IssueReport, Severity


_CODE_TOKEN_RE = re.compile(r"^(?P<code>[A-Za-z0-9][A-Za-z0-9_-]{0,15})\b")


@dataclass(frozen=True, slots=True)
class StatusLegend:
    codes: tuple[str, ...]
    labels_by_code: Mapping[str, str]
    meanings_by_code: Mapping[str, str] = field(default_factory=dict)

    def normalize_code(self, raw: str) -> str:
        """Normalize an arbitrary cell value into a canonical status code.

        This is intentionally tolerant of minor annotations in registries while
        still enforcing that the *code itself* is drawn from the legend.
        """

        s = strip_md_inline(raw or "").strip()
        if not s:
            return ""

        m = _CODE_TOKEN_RE.match(s)
        if m:
            return m.group("code").strip().upper()

        return s.upper()

    def is_valid_code(self, raw: str) -> bool:
        code = self.normalize_code(raw)
        return bool(code) and code in self.labels_by_code

    def label_for(self, code: str) -> str:
        return self.labels_by_code.get(code.strip().upper(), "")

    def meaning_for(self, code: str) -> str:
        return self.meanings_by_code.get(code.strip().upper(), "")

    def code_for_label(self, label: str) -> str | None:
        """Return the first code whose label exactly matches `label` (case-insensitive)."""

        want = label.strip().lower()
        for c in self.codes:
            if self.labels_by_code.get(c, "").strip().lower() == want:
                return c
        return None

    def code_for_label_prefix(self, prefix: str) -> str | None:
        """Return the first code whose label starts with `prefix` (case-insensitive)."""

        want = prefix.strip().lower()
        for c in self.codes:
            if self.labels_by_code.get(c, "").strip().lower().startswith(want):
                return c
        return None


def load_status_legend(path: Path) -> tuple[StatusLegend, IssueReport]:
    issues: list[Issue] = []

    if not path.exists():
        issues.append(Issue(Severity.ERROR, f"STATUS_LEGEND.md: missing: {path.as_posix()}"))
        return StatusLegend((), {}), IssueReport(tuple(issues))

    text = path.read_text(encoding="utf-8")
    table = find_table_by_headers(text, ["code", "label"])
    if table is None:
        issues.append(Issue(Severity.ERROR, 'STATUS_LEGEND.md: could not locate a table with "Code" and "Label" headers'))
        return StatusLegend((), {}), IssueReport(tuple(issues))

    code_col = find_column(table.header, "code")
    label_col = find_column(table.header, "label")
    meaning_col = find_column(table.header, "meaning")

    if code_col is None or label_col is None:
        issues.append(Issue(Severity.ERROR, "STATUS_LEGEND.md: table found, but could not resolve Code/Label columns"))
        return StatusLegend((), {}), IssueReport(tuple(issues))

    rows = table_rows_as_dicts(table)

    codes: list[str] = []
    labels: dict[str, str] = {}
    meanings: dict[str, str] = {}

    for r in rows:
        code_raw = r.get(code_col, "")
        label_raw = r.get(label_col, "")
        meaning_raw = r.get(meaning_col, "") if meaning_col else ""

        code = strip_md_inline(code_raw).strip().upper()
        label = strip_md_inline(label_raw).strip()
        meaning = strip_md_inline(meaning_raw).strip()

        if not code:
            continue

        if code in labels:
            if labels[code] != label:
                issues.append(
                    Issue(
                        Severity.WARN,
                        f"STATUS_LEGEND.md: duplicate code {code!r} with different labels ({labels[code]!r} vs {label!r}); using first",
                    )
                )
            continue

        codes.append(code)
        labels[code] = label
        if meaning:
            meanings[code] = meaning

    if not codes:
        issues.append(Issue(Severity.ERROR, "STATUS_LEGEND.md: no status codes found"))

    return StatusLegend(tuple(codes), labels, meanings), IssueReport(tuple(issues))


__all__ = ["StatusLegend", "load_status_legend"]
