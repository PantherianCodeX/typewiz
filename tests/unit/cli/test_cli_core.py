# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests exercising CLI helper normalization and formatting behavior."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from tests.fixtures.builders import build_diagnostic, build_readiness_summary
from typewiz._internal.utils import consume
from typewiz.cli.app import write_config_template
from typewiz.cli.commands.audit import normalise_modes_tuple
from typewiz.cli.helpers import (
    collect_plugin_args,
    collect_profile_args,
    normalise_modes,
    parse_summary_fields,
)
from typewiz.cli.helpers.formatting import (
    SUMMARY_FIELD_CHOICES,
    print_readiness_summary,
    print_summary,
    query_readiness,
)
from typewiz.core.model_types import (
    Mode,
    OverrideEntry,
    ReadinessLevel,
    ReadinessStatus,
    SummaryField,
    SummaryStyle,
)
from typewiz.core.summary_types import ReadinessOptionEntry, ReadinessStrictEntry, SummaryData
from typewiz.core.type_aliases import RelPath, ToolName
from typewiz.core.types import RunResult

pytestmark = [pytest.mark.unit, pytest.mark.cli]

PYRIGHT_TOOL = ToolName("pyright")
ALL_SUMMARY_FIELDS = sorted(SUMMARY_FIELD_CHOICES, key=lambda field: field.value)


def _sample_readiness_summary() -> SummaryData:
    option_entries = cast(
        dict[ReadinessStatus, list[ReadinessOptionEntry]],
        {
            ReadinessStatus.READY: [{"path": "pkg", "count": "not-a-number"}],
            ReadinessStatus.BLOCKED: [{"path": "pkg", "count": 2}],
        },
    )
    strict_entries = cast(
        dict[ReadinessStatus, list[ReadinessStrictEntry]],
        {
            ReadinessStatus.READY: [{"path": "pkg/module.py", "diagnostics": 0}],
            ReadinessStatus.BLOCKED: [{"path": "pkg/other.py", "diagnostics": "3"}],
        },
    )
    return build_readiness_summary(option_entries=option_entries, strict_entries=strict_entries)


def _build_cli_runs(tmp_path: Path) -> tuple[RunResult, RunResult]:
    diagnostic = build_diagnostic(path=tmp_path / "pkg" / "module.py")
    override_entry: OverrideEntry = {
        "path": "pkg",
        "profile": "strict",
        "pluginArgs": ["--warnings"],
        "include": [RelPath("src")],
        "exclude": [RelPath("tests")],
    }
    run_expanded = RunResult(
        tool=PYRIGHT_TOOL,
        mode=Mode.CURRENT,
        command=["pyright", "--project"],
        exit_code=0,
        duration_ms=0.1,
        diagnostics=[diagnostic],
        profile=None,
        config_file=None,
        plugin_args=["--strict"],
        include=[RelPath("pkg")],
        exclude=[],
        overrides=[override_entry],
    )
    run_present = RunResult(
        tool=PYRIGHT_TOOL,
        mode=Mode.FULL,
        command=["pyright", "."],
        exit_code=0,
        duration_ms=0.1,
        diagnostics=[],
        profile="strict",
        config_file=tmp_path / "pyrightconfig.json",
        plugin_args=[],
        include=[],
        exclude=[RelPath("legacy")],
        overrides=[override_entry],
    )
    return run_expanded, run_present


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" profile , , plugin-args ", [SummaryField.PROFILE, SummaryField.PLUGIN_ARGS]),
        ("all", ALL_SUMMARY_FIELDS),
    ],
)
def test_parse_summary_fields_normalises_input(raw: str, expected: list[SummaryField]) -> None:
    # Arrange
    valid_fields = SUMMARY_FIELD_CHOICES

    # Act
    result = parse_summary_fields(raw, valid_fields=valid_fields)

    # Assert
    assert result == expected


def test_parse_summary_fields_rejects_unknown_value() -> None:
    # Arrange
    raw = "profile,unknown"

    # Act / Assert
    with pytest.raises(SystemExit):
        consume(parse_summary_fields(raw, valid_fields=SUMMARY_FIELD_CHOICES))


def test_collect_plugin_args_merges_entries() -> None:
    # Arrange
    entries = ["pyright=--strict", "pyright:--warnings", "mypy = --strict "]

    # Act
    result = collect_plugin_args(entries)

    # Assert
    assert result == {"pyright": ["--strict", "--warnings"], "mypy": ["--strict"]}


@pytest.mark.parametrize(
    "entries",
    [
        ["pyright"],
        ["=--oops"],
        ["pyright="],
    ],
)
def test_collect_plugin_args_rejects_invalid_entries(entries: list[str]) -> None:
    # Act / Assert
    with pytest.raises(SystemExit):
        consume(collect_plugin_args(entries))


def test_collect_profile_args_records_mappings() -> None:
    # Arrange
    profile_args = ["pyright=strict", "mypy=baseline"]

    # Act
    profiles = collect_profile_args(profile_args)

    # Assert
    assert profiles == {"pyright": "strict", "mypy": "baseline"}


@pytest.mark.parametrize("entries", [["pyright"], ["pyright="]])
def test_collect_profile_args_rejects_invalid_entries(entries: list[str]) -> None:
    # Act / Assert
    with pytest.raises(SystemExit):
        consume(collect_profile_args(entries))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, (False, True, True)),
        (["current"], (True, True, False)),
    ],
)
def test_normalise_modes_tuple_handles_cli_flags(
    raw: list[str] | None, expected: tuple[bool, bool, bool]
) -> None:
    # Act
    result = normalise_modes_tuple(raw)

    # Assert
    assert result == expected


def test_normalise_modes_tuple_rejects_unknown_value() -> None:
    # Arrange
    raw = ["unknown"]

    # Act / Assert
    with pytest.raises(SystemExit):
        consume(normalise_modes_tuple(raw))


def test_normalise_modes_returns_modes_for_values() -> None:
    # Arrange
    requested = ["current", "full"]

    # Act
    modes = normalise_modes(requested)

    # Assert
    assert modes == [Mode.CURRENT, Mode.FULL]


def test_normalise_modes_returns_empty_when_not_requested() -> None:
    # Act
    modes = normalise_modes(None)

    # Assert
    assert modes == []


def test_write_config_template_preserves_existing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    target = tmp_path / "typewiz.toml"
    consume(target.write_text("original", encoding="utf-8"))

    # Act
    exit_code = write_config_template(target, force=False)

    # Assert
    assert exit_code == 1
    assert target.read_text(encoding="utf-8") == "original"
    output = capsys.readouterr().out
    assert "[typewiz] Refusing to overwrite" in output


def test_write_config_template_overwrites_when_forced(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    target = tmp_path / "typewiz.toml"
    consume(target.write_text("original", encoding="utf-8"))

    # Act
    exit_code = write_config_template(target, force=True)

    # Assert
    assert exit_code == 0
    assert "[typewiz] Wrote starter config" in capsys.readouterr().out
    assert "[audit]" in target.read_text(encoding="utf-8")


def test_print_readiness_summary_reports_folder_entries(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    summary = _sample_readiness_summary()

    # Act
    print_readiness_summary(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=[ReadinessStatus.BLOCKED, ReadinessStatus.CLOSE],
        limit=5,
    )

    # Assert
    output = capsys.readouterr().out
    assert "[typewiz] readiness folder status=blocked" in output
    assert "pkg: 2" in output
    assert "<none>" in output


def test_print_readiness_summary_reports_file_entries(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    summary = _sample_readiness_summary()

    # Act
    print_readiness_summary(
        summary,
        level=ReadinessLevel.FILE,
        statuses=[ReadinessStatus.READY, ReadinessStatus.BLOCKED],
        limit=1,
    )

    # Assert
    output = capsys.readouterr().out
    assert "pkg/module.py: 0" in output
    assert "pkg/other.py: 3" in output


def test_print_readiness_summary_defaults_to_blocked_when_limit_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    summary = _sample_readiness_summary()

    # Act
    print_readiness_summary(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=None,
        limit=0,
    )

    # Assert
    output = capsys.readouterr().out
    assert "[typewiz] readiness folder status=blocked" in output


def test_query_readiness_invalid_data_raises() -> None:
    # Arrange
    summary = build_readiness_summary(
        strict_entries={
            ReadinessStatus.BLOCKED: [
                {
                    "path": "pkg/module",
                    "diagnostics": -1,
                    "errors": 0,
                    "warnings": 0,
                    "information": 0,
                },
            ],
        },
    )

    # Act / Assert
    with pytest.raises(SystemExit):
        consume(
            query_readiness(
                summary,
                level=ReadinessLevel.FILE,
                statuses=[ReadinessStatus.BLOCKED],
                limit=5,
            ),
        )


def test_print_summary_expanded_style_includes_overrides(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    run_expanded, run_present = _build_cli_runs(tmp_path)

    # Act
    print_summary(
        [run_expanded, run_present],
        [
            SummaryField.PROFILE,
            SummaryField.CONFIG,
            SummaryField.PLUGIN_ARGS,
            SummaryField.PATHS,
            SummaryField.OVERRIDES,
        ],
        SummaryStyle.EXPANDED,
    )

    # Assert
    output = capsys.readouterr().out
    assert "override pkg" in output
    assert "profile: —" in output
    assert "config: —" in output


def test_print_summary_compact_style_includes_overrides(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    _, run_present = _build_cli_runs(tmp_path)

    # Act
    print_summary([run_present], [SummaryField.OVERRIDES], SummaryStyle.COMPACT)

    # Assert
    output = capsys.readouterr().out
    assert "overrides" in output
    assert "pyright:full exit=0" in output
