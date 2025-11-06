# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from .collection_utils import dedupe_preserve
from .utils import JSONValue


@dataclass(slots=True)
class Table:
    headers: list[str]
    rows: list[Mapping[str, JSONValue]]

    def render(self) -> list[str]:
        if not self.headers or not self.rows:
            return ["<empty>"]
        widths: dict[str, int] = {}
        for header in self.headers:
            max_len = max(len(header), *(len(stringify(row.get(header))) for row in self.rows))
            widths[header] = max_len
        header_line = " | ".join(header.ljust(widths[header]) for header in self.headers)
        separator = "-+-".join("-" * widths[header] for header in self.headers)
        lines = [header_line, separator]
        lines.extend(
            " | ".join(stringify(row.get(header)).ljust(widths[header]) for header in self.headers)
            for row in self.rows
        )
        return lines


def stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str | int | float):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Mapping):
        mapping = cast(Mapping[str, JSONValue], value)
        items: list[str] = []
        for key, val in mapping.items():
            items.append(f"{key}: {stringify(val)}")
        return "{" + ", ".join(items) + "}"
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence = cast(Sequence[JSONValue], value)
        return "[" + ", ".join(stringify(item) for item in sequence) + "]"
    return str(value)


def format_list(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "—"


def render_table_rows(rows: Sequence[Mapping[str, JSONValue]]) -> list[str]:
    if not rows:
        return ["<empty>"]
    headers = sorted({key for row in rows for key in row})
    table = Table(headers=headers, rows=list(rows))
    return table.render()


def dedupe_strings(values: Iterable[str]) -> list[str]:
    return dedupe_preserve(values)
