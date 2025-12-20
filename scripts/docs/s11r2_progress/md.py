"""Markdown parsing and rendering utilities for s11r2 governance files.

This module intentionally implements only the subset of Markdown we need for
s11r2 governance artifacts:

- GitHub-flavored pipe tables (for registries)
- Basic inline code / emphasis stripping (for cell normalization)
- Link extraction (for registry_index path discovery)

Generated-block insertion is handled by `scripts/docs/_generated_blocks.py` and
wrapped by :mod:`scripts.docs.s11r2_progress.generated_blocks`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import re


@dataclass(frozen=True, slots=True)
class MdTable:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    start_line: int  # 1-indexed
    end_line: int  # exclusive, 1-indexed


_PIPE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_SEP_ROW_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
_EMPHASIS_RE = re.compile(r"\*\*(?P<x>[^*]+)\*\*")
_LINK_RE = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<target>[^)]+)\)")


def split_pipe_row(line: str) -> list[str]:
    s = line.strip()
    s = s.removeprefix("|").removesuffix("|")
    return [p.strip() for p in s.split("|")]


def iter_md_tables(text: str) -> Iterable[MdTable]:
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        if _PIPE_ROW_RE.match(lines[i]) and _SEP_ROW_RE.match(lines[i + 1]):
            header = split_pipe_row(lines[i])
            sep = split_pipe_row(lines[i + 1])
            if len(header) != len(sep):
                i += 1
                continue

            rows: list[tuple[str, ...]] = []
            j = i + 2
            while j < len(lines) and _PIPE_ROW_RE.match(lines[j]):
                row = split_pipe_row(lines[j])
                if len(row) == len(header):
                    rows.append(tuple(row))
                j += 1

            yield MdTable(tuple(header), tuple(rows), i + 1, j + 1)
            i = j
            continue

        i += 1


def find_table_by_headers(text: str, required_fragments: Iterable[str]) -> MdTable | None:
    req = [r.strip().lower() for r in required_fragments]
    for t in iter_md_tables(text):
        header_lc = [h.lower() for h in t.header]
        if all(any(r in h for h in header_lc) for r in req):
            return t
    return None


def table_rows_as_dicts(table: MdTable) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in table.rows:
        out.append(dict(zip(table.header, row, strict=True)))
    return out


def find_column(headers: Iterable[str], fragment: str) -> str | None:
    frag = fragment.strip().lower()
    for h in headers:
        if frag in h.lower():
            return h
    return None


def strip_md_inline(text: str) -> str:
    """Remove the simplest inline wrappers used in registries.

    Supported:
    - bold emphasis: **NS**
    - inline code: `NS`

    The function is intentionally conservative: it does not attempt full
    Markdown parsing.
    """

    s = text.strip()
    m = _EMPHASIS_RE.fullmatch(s)
    if m:
        s = m.group("x").strip()
    if s.startswith("`") and s.endswith("`") and len(s) >= 2:
        s = s[1:-1].strip()
    return s


def extract_links(md: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in _LINK_RE.finditer(md):
        out.append((m.group("text").strip(), m.group("target").strip()))
    return out


def render_md_table(headers: Iterable[str], rows: Iterable[Iterable[str]], *, right_align: set[int] | None = None) -> str:
    header_list = list(headers)
    align = right_align or set()

    def _sep_cell(idx: int) -> str:
        return "---:" if idx in align else "---"

    lines: list[str] = []
    lines.append("| " + " | ".join(header_list) + " |")
    lines.append("| " + " | ".join(_sep_cell(i) for i in range(len(header_list))) + " |")

    for row in rows:
        cells = list(row)
        if len(cells) != len(header_list):
            raise ValueError(f"Row has {len(cells)} cells; expected {len(header_list)}")
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def render_labeled_bullets(items: Iterable[str], *, label: str) -> str:
    """Render items as a compact bullet list with a bold label per row."""

    out = [f"- **{label}**: {i}" for i in items]
    return "\n".join(out)


def extract_first_table_block(text: str) -> str | None:
    """Extract the first Markdown table block in text, including header+rows."""

    lines = text.splitlines()
    for i in range(len(lines) - 1):
        if not _PIPE_ROW_RE.match(lines[i]):
            continue
        if not _SEP_ROW_RE.match(lines[i + 1]):
            continue
        j = i + 2
        while j < len(lines) and _PIPE_ROW_RE.match(lines[j]):
            j += 1
        block = "\n".join(lines[i:j]).rstrip() + "\n"
        return block
    return None


__all__ = [
    "MdTable",
    "extract_first_table_block",
    "extract_links",
    "find_column",
    "find_table_by_headers",
    "iter_md_tables",
    "render_labeled_bullets",
    "render_md_table",
    "split_pipe_row",
    "strip_md_inline",
    "table_rows_as_dicts",
]
