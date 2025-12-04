# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from tests.fixtures.builders import build_empty_summary
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
    SeverityLevel,
    SummaryField,
    SummaryStyle,
)
from typewiz.core.summary_types import (
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
)
from typewiz.core.type_aliases import CategoryKey, RelPath, ToolName
from typewiz.core.types import Diagnostic, RunResult

PYRIGHT_TOOL = ToolName("pyright")


def test_parse_summary_fields_variants() -> None:
    fields = parse_summary_fields(" profile , , plugin-args ", valid_fields=SUMMARY_FIELD_CHOICES)
    assert fields == [SummaryField.PROFILE, SummaryField.PLUGIN_ARGS]

    all_fields = parse_summary_fields("all", valid_fields=SUMMARY_FIELD_CHOICES)
    assert all_fields == sorted(SUMMARY_FIELD_CHOICES, key=lambda field: field.value)

    with pytest.raises(SystemExit):
        consume(parse_summary_fields("profile,unknown", valid_fields=SUMMARY_FIELD_CHOICES))


def test_collect_plugin_args_variants() -> None:
    result = collect_plugin_args(["pyright=--strict", "pyright:--warnings", "mypy = --strict "])
    assert result == {"pyright": ["--strict", "--warnings"], "mypy": ["--strict"]}

    with pytest.raises(SystemExit):
        consume(collect_plugin_args(["pyright"]))
    with pytest.raises(SystemExit):
        consume(collect_plugin_args(["=--oops"]))
    with pytest.raises(SystemExit):
        consume(collect_plugin_args(["pyright="]))


def test_collect_profile_args_variants() -> None:
    profiles = collect_profile_args(["pyright=strict", "mypy=baseline"])
    assert profiles == {"pyright": "strict", "mypy": "baseline"}

    with pytest.raises(SystemExit):
        consume(collect_profile_args(["pyright"]))
    with pytest.raises(SystemExit):
        consume(collect_profile_args(["pyright="]))


def test_normalise_modes_variants() -> None:
    default_selection = normalise_modes_tuple(None)
    assert default_selection == (False, True, True)

    current_only = normalise_modes_tuple(["current"])
    assert current_only == (True, True, False)

    with pytest.raises(SystemExit):
        consume(normalise_modes_tuple(["unknown"]))

    assert normalise_modes(None) == []
    assert normalise_modes(["current", "full"]) == [Mode.CURRENT, Mode.FULL]


def test_write_config_template(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "typewiz.toml"
    consume(target.write_text("original", encoding="utf-8"))
    result = write_config_template(target, force=False)
    assert result == 1
    assert target.read_text(encoding="utf-8") == "original"
    output = capsys.readouterr().out
    assert "[typewiz] Refusing to overwrite" in output

    result_force = write_config_template(target, force=True)
    assert result_force == 0
    assert "[typewiz] Wrote starter config" in capsys.readouterr().out
    assert "[audit]" in target.read_text(encoding="utf-8")


def test_print_readiness_summary_variants(capsys: pytest.CaptureFixture[str]) -> None:
    summary = build_empty_summary()
    readiness_tab = summary["tabs"]["readiness"]
    readiness_tab["options"] = cast(
        dict[CategoryKey, ReadinessOptionsPayload],
        {
            "unknownChecks": {
                "threshold": 0,
                "buckets": {
                    ReadinessStatus.READY: cast(
                        tuple[ReadinessOptionEntry, ...],
                        ({"path": "pkg", "count": "not-a-number"},),
                    ),
                    ReadinessStatus.CLOSE: (),
                    ReadinessStatus.BLOCKED: cast(
                        tuple[ReadinessOptionEntry, ...],
                        ({"path": "pkg", "count": 2},),
                    ),
                },
            },
        },
    )
    readiness_tab["strict"] = cast(
        dict[ReadinessStatus, list[ReadinessStrictEntry]],
        {
            ReadinessStatus.READY: [{"path": "pkg/module.py", "diagnostics": 0}],
            ReadinessStatus.CLOSE: [],
            ReadinessStatus.BLOCKED: [{"path": "pkg/other.py", "diagnostics": "3"}],
        },
    )

    print_readiness_summary(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=[ReadinessStatus.BLOCKED, ReadinessStatus.CLOSE],
        limit=5,
    )
    output_folder = capsys.readouterr().out
    assert "[typewiz] readiness folder status=blocked" in output_folder
    assert "pkg: 2" in output_folder
    assert "<none>" in output_folder

    print_readiness_summary(
        summary,
        level=ReadinessLevel.FILE,
        statuses=[ReadinessStatus.READY, ReadinessStatus.BLOCKED],
        limit=1,
    )
    output_file = capsys.readouterr().out
    assert "pkg/module.py: 0" in output_file
    assert "pkg/other.py: 3" in output_file

    print_readiness_summary(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=None,
        limit=0,
    )
    fallback_output = capsys.readouterr().out
    assert "[typewiz] readiness folder status=blocked" in fallback_output


def test_query_readiness_invalid_data_raises() -> None:
    summary = build_empty_summary()
    readiness_tab = summary["tabs"]["readiness"]
    readiness_tab["strict"] = {
        ReadinessStatus.BLOCKED: [
            {
                "path": "pkg/module",
                "diagnostics": -1,
                "errors": 0,
                "warnings": 0,
                "information": 0,
            },
        ],
    }
    with pytest.raises(SystemExit):
        consume(
            query_readiness(
                summary,
                level=ReadinessLevel.FILE,
                statuses=[ReadinessStatus.BLOCKED],
                limit=5,
            ),
        )


def test_print_summary_styles(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    diag = Diagnostic(
        tool=PYRIGHT_TOOL,
        severity=SeverityLevel.ERROR,
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="reportGeneralTypeIssues",
        message="boom",
    )

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
        diagnostics=[diag],
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
    expanded_out = capsys.readouterr().out
    assert "override pkg" in expanded_out
    assert "profile: —" in expanded_out
    assert "config: —" in expanded_out

    print_summary([run_present], [SummaryField.OVERRIDES], SummaryStyle.COMPACT)
    compact_out = capsys.readouterr().out
    assert "overrides" in compact_out
    assert "pyright:full exit=0" in compact_out
