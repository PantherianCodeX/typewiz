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

"""Unit tests for Models Enums."""

from __future__ import annotations

from typing import Protocol, cast

import pytest

from ratchetr.core.model_types import (
    DashboardFormat,
    DashboardView,
    DataFormat,
    FailOnPolicy,
    HotspotKind,
    LicenseMode,
    LogComponent,
    LogFormat,
    ManifestAction,
    Mode,
    OverrideEntry,
    QuerySection,
    RatchetAction,
    ReadinessLevel,
    ReadinessStatus,
    SeverityLevel,
    SignaturePolicy,
    SummaryField,
    SummaryStyle,
    SummaryTabName,
    clone_override_entries,
)
from ratchetr.core.type_aliases import RelPath

pytestmark = pytest.mark.unit


class _SupportsFromStr(Protocol):
    @classmethod
    def from_str(cls, raw: str) -> object: ...


EnumType = type[_SupportsFromStr]


def test_cli_enums_accept_case_insensitive_values() -> None:
    assert RatchetAction.from_str("INIT") is RatchetAction.INIT
    assert ManifestAction.from_str("Schema") is ManifestAction.SCHEMA
    assert QuerySection.from_str("Runs") is QuerySection.RUNS


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("CURRENT", Mode.CURRENT),
        ("full", Mode.FULL),
    ],
)
def test_mode_from_str_accepts_variants(value: str, expected: Mode) -> None:
    assert Mode.from_str(value) is expected


def test_mode_from_str_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown mode"):
        _ = Mode.from_str("invalid-mode")


def test_readiness_status_from_str_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown readiness status"):
        _ = ReadinessStatus.from_str("unknown")


def test_data_format_from_str_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown data format"):
        _ = DataFormat.from_str("binary")


def test_summary_tab_name_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown summary tab"):
        _ = SummaryTabName.from_str("invalid")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ERROR", SeverityLevel.ERROR),
        ("warning", SeverityLevel.WARNING),
        ("Info", SeverityLevel.INFORMATION),
        ("infos", SeverityLevel.INFORMATION),
        ("unknown", SeverityLevel.INFORMATION),
    ],
)
def test_severity_level_coerce_handles_synonyms(value: str, expected: SeverityLevel) -> None:
    assert SeverityLevel.coerce(value) is expected


def test_severity_level_coerce_plural_and_alias() -> None:
    assert SeverityLevel.coerce("errors") is SeverityLevel.ERROR
    assert SeverityLevel.coerce("info") is SeverityLevel.INFORMATION


@pytest.mark.parametrize(
    ("value", "enum_cls"),
    [
        ("blocked", ReadinessStatus),
        ("folder", ReadinessLevel),
        ("files", HotspotKind),
        ("json", DashboardFormat),
        ("json", DataFormat),
        ("text", LogFormat),
        ("cli", LogComponent),
        ("compact", SummaryStyle),
        ("profile", SummaryField),
        ("engines", SummaryTabName),
        ("errors", FailOnPolicy),
        ("fail", SignaturePolicy),
        ("validate", ManifestAction),
        ("runs", QuerySection),
        ("commercial", LicenseMode),
        ("readiness", DashboardView),
    ],
)
def test_various_enum_parsers_accept_values(value: str, enum_cls: EnumType) -> None:
    assert enum_cls.from_str(value)


@pytest.mark.parametrize(
    "enum_cls",
    [
        LogFormat,
        LogComponent,
        LicenseMode,
        DashboardFormat,
        DashboardView,
        ReadinessLevel,
        HotspotKind,
        SummaryStyle,
        SummaryField,
        SignaturePolicy,
        FailOnPolicy,
        RatchetAction,
        ManifestAction,
        QuerySection,
    ],
)
def test_various_enums_reject_unknown_values(enum_cls: EnumType) -> None:
    with pytest.raises(ValueError, match="not-a-real-option"):
        _ = enum_cls.from_str("not-a-real-option")


def test_severity_level_coerce_returns_existing_instance() -> None:
    existing = SeverityLevel.ERROR
    assert SeverityLevel.coerce(existing) is existing


def test_clone_override_entries_returns_copies() -> None:
    entries: list[OverrideEntry] = [
        cast(
            "OverrideEntry",
            {"path": "apps", "include": [RelPath("pkg")], "pluginArgs": ["--strict"]},
        ),
    ]
    cloned = clone_override_entries(entries)
    assert cloned == entries
    cloned[0]["pluginArgs"] = ["--relaxed"]
    assert entries[0].get("pluginArgs") == ["--strict"]
