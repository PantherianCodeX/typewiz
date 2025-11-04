from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict, cast

type Mode = Literal["current", "full"]
type SeverityLevel = Literal["error", "warning", "information"]

type CategoryMapping = dict[str, list[str]]


class OverrideEntry(TypedDict, total=False):
    path: str
    profile: str
    pluginArgs: list[str]
    include: list[str]
    exclude: list[str]


class DiagnosticPayload(TypedDict, total=False):
    tool: str
    severity: str
    path: str
    line: int
    column: int
    code: str | None
    message: str
    raw: dict[str, object]


class FileHashPayload(TypedDict, total=False):
    hash: str
    mtime: int
    size: int
    missing: bool
    unreadable: bool


def clone_override_entries(entries: Sequence[OverrideEntry]) -> list[OverrideEntry]:
    return [cast(OverrideEntry, dict(entry)) for entry in entries]
