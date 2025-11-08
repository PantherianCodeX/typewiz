# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import json
import sys
import types
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from typewiz._internal.utils import consume
from typewiz.api import AuditResult
from typewiz.cli.app import main, write_config_template
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
from typewiz.config import Config
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
    CountsByCategory,
    CountsByRule,
    CountsBySeverity,
    EnginesTab,
    HotspotsTab,
    OverviewTab,
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
    ReadinessTab,
    RunsTab,
    SummaryData,
    SummaryFileEntry,
    SummaryFolderEntry,
    SummaryRunEntry,
    SummaryTabs,
)
from typewiz.core.type_aliases import CategoryKey, EngineName, RelPath, RunId, RunnerName, ToolName
from typewiz.core.types import Diagnostic, RunResult
from typewiz.engines.base import EngineContext, EngineResult
from typewiz.manifest.versioning import CURRENT_MANIFEST_VERSION

_print_summary = print_summary
_print_readiness_summary = print_readiness_summary
_query_readiness = query_readiness
_write_config_template = write_config_template
_normalise_modes_cli = normalise_modes_tuple
STUB_TOOL = ToolName("stub")
PYRIGHT_ENGINE = EngineName("pyright")
PYRIGHT_RUNNER = RunnerName(PYRIGHT_ENGINE)
PYRIGHT_TOOL = ToolName("pyright")


def _write_manifest(tmp_path: Path) -> Path:
    manifest: dict[str, object] = {
        "generatedAt": "2025-11-05T00:00:00Z",
        "projectRoot": str(tmp_path),
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [
            {
                "tool": "pyright",
                "mode": "current",
                "command": ["pyright", "--project"],
                "exitCode": 1,
                "durationMs": 12,
                "summary": {
                    "errors": 4,
                    "warnings": 2,
                    "information": 0,
                    "total": 6,
                    "severityBreakdown": {"error": 4, "warning": 2},
                    "ruleCounts": {"reportGeneralTypeIssues": 4},
                    "categoryCounts": {"unknownChecks": 4},
                },
                "engineOptions": {
                    "profile": "strict",
                    "configFile": "pyrightconfig.json",
                    "pluginArgs": ["--strict"],
                    "include": [RelPath("src")],
                    "exclude": [RelPath("tests")],
                    "overrides": [{"path": "src", "profile": "strict"}],
                    "categoryMapping": {"unknownChecks": ["reportGeneralTypeIssues"]},
                },
                "perFolder": [
                    {
                        "path": "src",
                        "depth": 1,
                        "errors": 3,
                        "warnings": 2,
                        "information": 0,
                        "codeCounts": {"reportGeneralTypeIssues": 4},
                        "categoryCounts": {"unknownChecks": 4},
                        "recommendations": ["add type annotations"],
                    },
                ],
                "perFile": [
                    {
                        "path": "src/app.py",
                        "errors": 3,
                        "warnings": 0,
                        "information": 0,
                        "diagnostics": [
                            {
                                "line": 10,
                                "column": 4,
                                "severity": "error",
                                "code": "reportGeneralTypeIssues",
                                "message": "strict mode failure",
                            },
                        ],
                    },
                    {
                        "path": "src/utils.py",
                        "errors": 0,
                        "warnings": 2,
                        "information": 0,
                        "diagnostics": [
                            {
                                "line": 20,
                                "column": 2,
                                "severity": "warning",
                                "code": "reportUnknownVariableType",
                                "message": "graduated warning",
                            },
                        ],
                    },
                ],
            },
            {
                "tool": "mypy",
                "mode": "full",
                "command": ["mypy", "--strict"],
                "exitCode": 0,
                "durationMs": 15,
                "summary": {
                    "errors": 0,
                    "warnings": 1,
                    "information": 1,
                    "total": 2,
                    "severityBreakdown": {"warning": 1, "information": 1},
                    "ruleCounts": {"attr-defined": 1},
                    "categoryCounts": {"general": 1},
                },
                "engineOptions": {
                    "profile": "baseline",
                    "configFile": "mypy.ini",
                    "pluginArgs": [],
                    "include": [RelPath("src")],
                    "exclude": [],
                    "overrides": [],
                    "categoryMapping": {},
                },
                "perFolder": [
                    {
                        "path": "src",
                        "depth": 1,
                        "errors": 0,
                        "warnings": 1,
                        "information": 1,
                        "codeCounts": {"attr-defined": 1},
                        "categoryCounts": {"general": 1},
                        "recommendations": [],
                    },
                ],
                "perFile": [
                    {
                        "path": "src/app.py",
                        "errors": 0,
                        "warnings": 1,
                        "information": 1,
                        "diagnostics": [
                            {
                                "line": 30,
                                "column": 6,
                                "severity": "warning",
                                "code": "attr-defined",
                                "message": "attr-defined warning",
                            },
                            {
                                "line": 32,
                                "column": 1,
                                "severity": "information",
                                "code": "note",
                                "message": "note",
                            },
                        ],
                    },
                ],
            },
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    consume(manifest_path.write_text(json.dumps(manifest), encoding="utf-8"))
    return manifest_path


def _empty_summary() -> SummaryData:
    run_summary: dict[RunId, SummaryRunEntry] = {}
    severity_totals: CountsBySeverity = {}
    category_totals: CountsByCategory = {}
    top_rules: CountsByRule = {}
    overview: OverviewTab = {
        "severityTotals": severity_totals,
        "categoryTotals": category_totals,
        "runSummary": run_summary,
    }
    engines: EnginesTab = {"runSummary": run_summary}
    top_folders: list[SummaryFolderEntry] = []
    top_files: list[SummaryFileEntry] = []
    hotspots: HotspotsTab = {
        "topRules": top_rules,
        "topFolders": top_folders,
        "topFiles": top_files,
        "ruleFiles": {},
    }
    readiness: ReadinessTab = {
        "strict": {
            ReadinessStatus.READY: [],
            ReadinessStatus.CLOSE: [],
            ReadinessStatus.BLOCKED: [],
        },
        "options": {},
    }
    runs: RunsTab = {"runSummary": run_summary}
    tabs: SummaryTabs = {
        "overview": overview,
        "engines": engines,
        "hotspots": hotspots,
        "readiness": readiness,
        "runs": runs,
    }
    summary: SummaryData = {
        "generatedAt": "now",
        "projectRoot": ".",
        "runSummary": run_summary,
        "severityTotals": severity_totals,
        "categoryTotals": category_totals,
        "topRules": top_rules,
        "topFolders": top_folders,
        "topFiles": top_files,
        "ruleFiles": {},
        "tabs": tabs,
    }
    return summary


class StubEngine:
    def __init__(self, result: RunResult, expected_profile: str | None = None) -> None:
        super().__init__()
        self.name = "stub"
        self._result = result
        self.expected_profile = expected_profile
        self.invocations: list[tuple[Mode, list[str], list[str]]] = []

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        if self.expected_profile is not None:
            assert context.engine_options.profile == self.expected_profile
        self.invocations.append(
            (context.mode, list(context.engine_options.plugin_args), list(paths)),
        )
        tool_name = ToolName(self.name)
        if context.mode is Mode.FULL:
            return EngineResult(
                engine=tool_name,
                mode=context.mode,
                command=["stub", *paths],
                exit_code=0,
                duration_ms=0.2,
                diagnostics=[],
            )
        return EngineResult(
            engine=tool_name,
            mode=context.mode,
            command=list(self._result.command),
            exit_code=self._result.exit_code,
            duration_ms=self._result.duration_ms,
            diagnostics=list(self._result.diagnostics),
        )

    def category_mapping(self) -> dict[str, list[str]]:
        return {}

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        return []


def _patch_engine_resolution(monkeypatch: pytest.MonkeyPatch, engine: StubEngine) -> None:
    def _resolve(_: Sequence[str]) -> list[StubEngine]:
        return [engine]

    monkeypatch.setattr("typewiz.engines.resolve_engines", _resolve)
    monkeypatch.setattr("typewiz.api.resolve_engines", _resolve)


@pytest.fixture
def fake_run(tmp_path: Path) -> RunResult:
    (tmp_path / "pkg").mkdir(exist_ok=True)
    diag = Diagnostic(
        tool=STUB_TOOL,
        severity=SeverityLevel.ERROR,
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="reportGeneralTypeIssues",
        message="oops",
        raw={},
    )
    return RunResult(
        tool=STUB_TOOL,
        mode=Mode.CURRENT,
        command=["stub"],
        exit_code=1,
        duration_ms=1.0,
        diagnostics=[diag],
    )


def test_cli_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run: RunResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = StubEngine(fake_run, expected_profile="strict")
    _patch_engine_resolution(monkeypatch, engine)

    (tmp_path / "pkg").mkdir(exist_ok=True)
    consume((tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8"))

    manifest_path = tmp_path / "manifest.json"
    dashboard_path = tmp_path / "dashboard.md"
    consume(dashboard_path.write_text("stale", encoding="utf-8"))
    exit_code = main(
        [
            "audit",
            "--runner",
            "stub",
            "--project-root",
            str(tmp_path),
            "pkg",
            "--manifest",
            str(manifest_path),
            "--dashboard-markdown",
            str(dashboard_path),
            "--fail-on",
            "warnings",
            "--profile",
            "stub",
            "strict",
            "--plugin-arg",
            "stub=--cli-flag",
            "--summary",
            "compact",
        ],
    )

    captured = capsys.readouterr()

    assert exit_code == 2  # fail on warnings triggered (error counts)
    assert manifest_path.exists()
    assert dashboard_path.exists()
    assert dashboard_path.read_text(encoding="utf-8") != "stale"
    assert any(mode is Mode.FULL for mode, _, _ in engine.invocations)
    assert all("--cli-flag" in args for _, args, _ in engine.invocations)

    manifest_json = cast(dict[str, object], json.loads(manifest_path.read_text(encoding="utf-8")))
    runs_value = manifest_json.get("runs")
    assert isinstance(runs_value, list)
    assert runs_value
    first_run = cast(dict[str, object], runs_value[0])
    engine_options_obj = cast(dict[str, object], first_run.get("engineOptions", {}))
    assert engine_options_obj.get("profile") == "strict"
    assert engine_options_obj.get("pluginArgs") == ["--cli-flag"]
    assert "profile=" not in captured.out


def test_cli_dashboard_output(tmp_path: Path) -> None:
    manifest: dict[str, object] = {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": str(tmp_path),
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    manifest_path = tmp_path / "manifest.json"
    consume(manifest_path.write_text(json.dumps(manifest), encoding="utf-8"))

    exit_code = main(
        [
            "dashboard",
            "--manifest",
            str(manifest_path),
            "--format",
            "json",
        ],
    )
    assert exit_code == 0


def test_cli_version_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TYPEWIZ_LICENSE_KEY", "test")
    exit_code = main(["--version"])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "typewiz" in output.lower()


def test_cli_engines_list(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TYPEWIZ_LICENSE_KEY", "test")
    exit_code = main(["engines", "list", "--format", "json"])
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert any(entry["name"] == "pyright" for entry in data)


def test_cli_cache_clear(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_dir = tmp_path / ".typewiz_cache"
    cache_dir.mkdir()
    consume((cache_dir / "cache.json").write_text("{}", encoding="utf-8"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TYPEWIZ_LICENSE_KEY", "test")
    exit_code = main(["cache", "clear"])
    assert exit_code == 0
    assert not cache_dir.exists()


def test_cli_audit_readiness_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run: RunResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = StubEngine(fake_run)
    _patch_engine_resolution(monkeypatch, engine)

    (tmp_path / "pkg").mkdir(exist_ok=True)
    consume((tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8"))

    manifest_path = tmp_path / "manifest.json"
    exit_code = main(
        [
            "audit",
            "--runner",
            "stub",
            "--project-root",
            str(tmp_path),
            "pkg",
            "--manifest",
            str(manifest_path),
            "--fail-on",
            "never",
            "--readiness",
            "--readiness-status",
            "blocked",
            "--readiness-status",
            "ready",
            "--readiness-limit",
            "2",
        ],
    )

    assert exit_code == 0

    captured = capsys.readouterr()
    assert "[typewiz] readiness folder status=blocked" in captured.out
    assert "pkg" in captured.out

    exit_code_readiness = main(
        [
            "readiness",
            "--manifest",
            str(manifest_path),
            "--level",
            "file",
            "--status",
            "blocked",
            "--status",
            "ready",
            "--limit",
            "1",
        ],
    )
    assert exit_code_readiness == 0
    readiness_output = capsys.readouterr().out
    assert "[typewiz] readiness file status=blocked" in readiness_output


def test_cli_readiness_details_and_severity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "readiness",
            "--manifest",
            str(manifest_path),
            "--level",
            "file",
            "--status",
            "blocked",
            "--severity",
            "warning",
            "--details",
        ],
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "warnings=" in output


def test_cli_summary_extras(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run: RunResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = StubEngine(fake_run, expected_profile="strict")
    _patch_engine_resolution(monkeypatch, engine)

    (tmp_path / "pkg").mkdir(exist_ok=True)
    consume((tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8"))
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "extras").mkdir(exist_ok=True)
    config_path = tmp_path / "typewiz.toml"
    consume(
        config_path.write_text(
            """
[audit]
full_paths = ["src"]

[audit.engines.stub]
include = ["extras"]

[audit.engines.stub.profiles.strict]
plugin_args = ["--strict"]
""",
            encoding="utf-8",
        ),
    )
    override_path = tmp_path / "extras" / "typewiz.dir.toml"
    consume(
        override_path.write_text(
            """
[active_profiles]
stub = "strict"

[engines.stub]
plugin_args = ["--extras"]
exclude = ["unused"]
""",
            encoding="utf-8",
        ),
    )

    manifest_path = tmp_path / "manifest.json"
    dashboard_path = tmp_path / "dashboard.md"
    monkeypatch.chdir(tmp_path)
    exit_code = main(
        [
            "audit",
            "--runner",
            "stub",
            "src",
            "--manifest",
            str(manifest_path),
            "--dashboard-markdown",
            str(dashboard_path),
            "--profile",
            "stub",
            "strict",
            "--plugin-arg",
            "stub=--cli-flag",
            "--summary",
            "expanded",
            "--summary-fields",
            "profile,plugin-args,paths",
        ],
    )

    assert exit_code == 0

    captured = capsys.readouterr()
    assert "- profile: strict" in captured.out
    assert "- plugin args: --cli-flag, --strict, --extras" in captured.out
    assert "- include: extras" in captured.out
    assert "- exclude: extras/unused" in captured.out
    assert "- config" not in captured.out

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    full_run = next(run for run in manifest_data["runs"] if run["mode"] == "full")
    engine_options = full_run["engineOptions"]
    assert "--extras" in engine_options["pluginArgs"]


def test_cli_audit_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run: RunResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = StubEngine(fake_run)
    _patch_engine_resolution(monkeypatch, engine)

    (tmp_path / "pkg").mkdir(exist_ok=True)
    consume((tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8"))
    manifest_path = tmp_path / "manifest.json"

    exit_code = main(
        [
            "audit",
            "--runner",
            "stub",
            "--project-root",
            str(tmp_path),
            "pkg",
            "--manifest",
            str(manifest_path),
            "--dry-run",
        ],
    )

    assert exit_code == 0
    assert not manifest_path.exists()
    output = capsys.readouterr().out
    assert "--dry-run enabled" in output


def test_cli_audit_hash_workers_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recorded: dict[str, object] = {}

    sample_summary = cast(
        SummaryData,
        {
            "generatedAt": "now",
            "projectRoot": str(tmp_path),
            "runSummary": {},
            "severityTotals": {},
            "categoryTotals": {},
            "topRules": {},
            "topFolders": [],
            "topFiles": [],
            "ruleFiles": {},
            "tabs": {
                "overview": {"severityTotals": {}, "categoryTotals": {}, "runSummary": {}},
                "engines": {"runSummary": {}},
                "hotspots": {
                    "topRules": {},
                    "topFolders": [],
                    "topFiles": [],
                    "ruleFiles": {},
                },
                "readiness": {"strict": {}, "options": {}},
                "runs": {"runSummary": {}},
            },
        },
    )

    def _run_audit_stub(**kwargs: object) -> AuditResult:
        recorded["override"] = kwargs.get("override")
        return AuditResult(
            manifest={"schemaVersion": CURRENT_MANIFEST_VERSION, "runs": []},
            runs=[],
            summary=sample_summary,
            error_count=0,
            warning_count=0,
        )

    def _noop(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr("typewiz.cli.commands.audit.run_audit", _run_audit_stub)
    monkeypatch.setattr("typewiz.cli.commands.audit.print_summary", _noop)
    monkeypatch.setattr("typewiz.cli.commands.audit._maybe_print_readiness", _noop)

    (tmp_path / "pkg").mkdir(exist_ok=True)
    consume((tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8"))

    exit_code = main(
        [
            "audit",
            "--runner",
            "stub",
            "--project-root",
            str(tmp_path),
            "pkg",
            "--hash-workers",
            "auto",
        ],
    )
    assert exit_code == 0
    override = recorded["override"]
    assert override is not None
    assert getattr(override, "hash_workers", None) == "auto"


def test_cli_mode_only_full(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run: RunResult,
) -> None:
    engine = StubEngine(fake_run)
    _patch_engine_resolution(monkeypatch, engine)

    (tmp_path / "pkg").mkdir(exist_ok=True)

    exit_code = main(
        [
            "audit",
            "--runner",
            "stub",
            "--project-root",
            str(tmp_path),
            "--mode",
            "full",
            "pkg",
        ],
    )

    assert exit_code == 0
    assert engine.invocations == [(Mode.FULL, [], ["pkg"])]


def test_cli_plugin_arg_validation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = StubEngine(
        RunResult(
            tool=STUB_TOOL,
            mode=Mode.CURRENT,
            command=["stub"],
            exit_code=0,
            duration_ms=0.0,
            diagnostics=[],
        ),
    )
    _patch_engine_resolution(monkeypatch, engine)

    with pytest.raises(SystemExit):
        consume(
            main(
                [
                    "audit",
                    "--runner",
                    "stub",
                    "--project-root",
                    str(tmp_path),
                    "--plugin-arg",
                    "stub",
                ],
            ),
        )


def test_cli_init_writes_template(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "typewiz.toml"
    exit_code = main(["init", "--output", str(target)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Wrote starter config" in out
    assert target.exists()
    assert "config_version" in target.read_text(encoding="utf-8")


def test_cli_audit_without_markers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run: RunResult,
) -> None:
    engine = StubEngine(fake_run)
    _patch_engine_resolution(monkeypatch, engine)
    monkeypatch.chdir(tmp_path)

    (tmp_path / "pkg").mkdir(exist_ok=True)
    consume((tmp_path / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8"))

    exit_code = main(
        [
            "audit",
            "--runner",
            "stub",
            "pkg",
        ],
    )

    assert exit_code == 0
    # Fallback root detection should still run both modes
    assert {mode for mode, *_ in engine.invocations} == {Mode.CURRENT, Mode.FULL}


def test_cli_audit_requires_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = Config()

    def _load_config(_: Path | None = None) -> Config:
        return cfg

    def _default_paths(_: Path) -> list[str]:
        return []

    monkeypatch.setattr("typewiz.cli.commands.audit.load_config", _load_config)
    monkeypatch.setattr("typewiz.cli.commands.audit.default_full_paths", _default_paths)

    with pytest.raises(SystemExit):
        consume(main(["audit"]))


def test_cli_audit_full_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = Config()
    cfg.audit.runners = [PYRIGHT_RUNNER]

    summary = _empty_summary()
    summary["tabs"]["overview"]["severityTotals"] = {
        SeverityLevel.ERROR: 0,
        SeverityLevel.WARNING: 0,
        SeverityLevel.INFORMATION: 1,
    }
    prev_summary = _empty_summary()
    prev_summary["tabs"]["overview"]["severityTotals"] = {
        SeverityLevel.ERROR: 0,
        SeverityLevel.WARNING: 0,
        SeverityLevel.INFORMATION: 0,
    }

    diag = Diagnostic(
        tool=PYRIGHT_TOOL,
        severity=SeverityLevel.INFORMATION,
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="information",
        message="info",
    )
    override_entry_full: OverrideEntry = {"path": "pkg", "profile": "strict"}
    run = RunResult(
        tool=PYRIGHT_TOOL,
        mode=Mode.CURRENT,
        command=["pyright", "pkg"],
        exit_code=0,
        duration_ms=1.0,
        diagnostics=[diag],
        profile="strict",
        config_file=tmp_path / "pyrightconfig.json",
        plugin_args=["--strict"],
        include=[RelPath("pkg")],
        exclude=[],
        overrides=[override_entry_full],
        scanned_paths=[RelPath("pkg")],
    )
    audit_result = AuditResult(
        manifest={"schemaVersion": CURRENT_MANIFEST_VERSION, "runs": []},
        runs=[run],
        summary=summary,
        error_count=0,
        warning_count=0,
    )

    def _load_config(_: Path | None = None) -> Config:
        return cfg

    def _resolve_root(_: Path | None = None) -> Path:
        return tmp_path

    def _default_paths(_: Path) -> list[str]:
        return ["pkg"]

    def _run_audit_stub(**_: object) -> AuditResult:
        return audit_result

    def _render_markdown(_: object) -> str:
        return "markdown"

    def _render_html(_: object, default_view: str) -> str:
        assert default_view in {"engines", "overview", "hotspots", "readiness", "runs"}
        return "<html>"

    monkeypatch.setattr("typewiz.cli.commands.audit.load_config", _load_config)
    monkeypatch.setattr("typewiz.cli.commands.audit.resolve_project_root", _resolve_root)
    monkeypatch.setattr("typewiz.cli.commands.audit.default_full_paths", _default_paths)
    monkeypatch.setattr("typewiz.cli.commands.audit.run_audit", _run_audit_stub)
    monkeypatch.setattr("typewiz.services.dashboard.render_markdown", _render_markdown)
    monkeypatch.setattr("typewiz.services.dashboard.render_html", _render_html)

    def _fake_build_summary(data: object) -> SummaryData:
        if isinstance(data, dict):
            dict_data = cast(dict[str, object], data)
            if dict_data.get("__prev__"):
                return prev_summary
        return summary

    monkeypatch.setattr("typewiz.cli.commands.audit.build_summary", _fake_build_summary)

    def _load_prev_summary(_: Path) -> SummaryData:
        return prev_summary

    monkeypatch.setattr(
        "typewiz.cli.commands.audit.load_summary_from_manifest",
        _load_prev_summary,
    )

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    compare_path = tmp_path / "prev_manifest.json"
    consume(compare_path.write_text("{}", encoding="utf-8"))

    dashboard_json = tmp_path / "dashboard.json"
    dashboard_md = tmp_path / "dashboard.md"
    dashboard_html = tmp_path / "dashboard.html"

    exit_code = main(
        [
            "audit",
            "--runner",
            "pyright",
            "pkg",
            "--summary",
            "full",
            "--fail-on",
            "any",
            "--compare-to",
            str(compare_path),
            "--dashboard-json",
            str(dashboard_json),
            "--dashboard-markdown",
            str(dashboard_md),
            "--dashboard-html",
            str(dashboard_html),
            "--dashboard-view",
            "engines",
        ],
    )

    out = capsys.readouterr().out
    assert "delta: errors=0 warnings=0 info=+1" in out
    assert exit_code == 2
    assert dashboard_json.exists()
    assert dashboard_md.exists()
    assert dashboard_html.exists()


def test_cli_dashboard_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    consume(
        manifest_path.write_text(
            json.dumps({"schemaVersion": CURRENT_MANIFEST_VERSION, "runs": []}),
            encoding="utf-8",
        ),
    )

    summary = _empty_summary()

    def _build_summary(_: object) -> SummaryData:
        return summary

    def _render_markdown(_: object) -> str:
        return "markdown"

    def _render_html(_: object, default_view: str) -> str:
        assert default_view in {"overview", "engines", "hotspots", "readiness", "runs"}
        return "<html>"

    monkeypatch.setattr("typewiz.cli.app.build_summary", _build_summary)
    monkeypatch.setattr("typewiz.cli.app.render_markdown", _render_markdown)
    monkeypatch.setattr("typewiz.cli.app.render_html", _render_html)

    exit_code_json = main(["dashboard", "--manifest", str(manifest_path)])
    assert exit_code_json == 0
    out_json = capsys.readouterr().out
    assert json.loads(out_json) == summary

    md_path = tmp_path / "dashboard.md"
    exit_code_md = main(
        [
            "dashboard",
            "--manifest",
            str(manifest_path),
            "--format",
            "markdown",
            "--output",
            str(md_path),
        ],
    )
    assert exit_code_md == 0
    assert md_path.read_text(encoding="utf-8") == "markdown"

    html_path = tmp_path / "dashboard.html"
    exit_code_html = main(
        [
            "dashboard",
            "--manifest",
            str(manifest_path),
            "--format",
            "html",
            "--output",
            str(html_path),
            "--view",
            "engines",
        ],
    )
    assert exit_code_html == 0
    assert html_path.read_text(encoding="utf-8") == "<html>"


def test_cli_manifest_validate_with_jsonschema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    consume(
        manifest_path.write_text(
            json.dumps(
                {
                    "generatedAt": "now",
                    "projectRoot": ".",
                    "schemaVersion": CURRENT_MANIFEST_VERSION,
                    "runs": [],
                },
            ),
            encoding="utf-8",
        ),
    )
    schema_path = tmp_path / "schema.json"
    consume(schema_path.write_text(json.dumps({"type": "object"}), encoding="utf-8"))

    class DummyValidator:
        def __init__(self, schema: object) -> None:
            super().__init__()
            self.schema = schema

        def iter_errors(self, data: object) -> list[object]:
            return []

    dummy_module = types.SimpleNamespace(Draft7Validator=DummyValidator)
    monkeypatch.setitem(sys.modules, "jsonschema", dummy_module)

    exit_code = main(["manifest", "validate", str(manifest_path), "--schema", str(schema_path)])
    assert exit_code == 0
    assert "manifest is valid" in capsys.readouterr().out


def test_cli_manifest_validate_runs_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "bad.json"
    consume(
        manifest_path.write_text(
            json.dumps(
                {
                    "generatedAt": "now",
                    "projectRoot": ".",
                    "schemaVersion": CURRENT_MANIFEST_VERSION,
                    "runs": {},
                },
            ),
            encoding="utf-8",
        ),
    )

    exit_code = main(["manifest", "validate", str(manifest_path)])
    assert exit_code == 2
    output = capsys.readouterr().out
    assert "validation error at runs" in output
    assert "runs must be a list" in output


def test_cli_manifest_unknown_action(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_cmd = ["manifest", "unknown"]
    with pytest.raises(SystemExit):
        consume(main(manifest_cmd))


def test_cli_query_overview_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "query",
            "overview",
            "--manifest",
            str(manifest_path),
            "--include-runs",
            "--format",
            "table",
        ],
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "severity_totals" in output
    assert "pyright:current" in output


def test_cli_query_hotspots_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "query",
            "hotspots",
            "--manifest",
            str(manifest_path),
            "--kind",
            "folders",
            "--limit",
            "1",
        ],
    )
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["path"] == "src"
    assert data[0]["errors"] >= 1
    exit_code_files = main(
        [
            "query",
            "hotspots",
            "--manifest",
            str(manifest_path),
            "--kind",
            "files",
            "--limit",
            "2",
            "--format",
            "table",
        ],
    )
    assert exit_code_files == 0
    table_output = capsys.readouterr().out
    assert "src/app.py" in table_output


def test_cli_query_readiness_file_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "query",
            "readiness",
            "--manifest",
            str(manifest_path),
            "--level",
            "file",
            "--status",
            "blocked",
            "--format",
            "table",
        ],
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "blocked" in output
    assert "src" in output


def test_cli_query_readiness_folder_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "query",
            "readiness",
            "--manifest",
            str(manifest_path),
        ],
    )
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert "blocked" in data
    assert data["blocked"]


def test_cli_query_runs_filters(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "query",
            "runs",
            "--manifest",
            str(manifest_path),
            "--tool",
            "pyright",
            "--mode",
            "current",
            "--format",
            "json",
        ],
    )
    assert exit_code == 0
    runs = json.loads(capsys.readouterr().out)
    assert len(runs) == 1
    assert runs[0]["tool"] == "pyright"


def test_cli_query_runs_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "query",
            "runs",
            "--manifest",
            str(manifest_path),
            "--tool",
            "nonexistent",
            "--format",
            "table",
        ],
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "<empty>" in output


def test_cli_query_engines_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "query",
            "engines",
            "--manifest",
            str(manifest_path),
            "--format",
            "table",
        ],
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "pyright:current" in output
    assert "--strict" in output


def test_cli_query_rules_limit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = _write_manifest(tmp_path)
    exit_code = main(
        [
            "query",
            "rules",
            "--manifest",
            str(manifest_path),
            "--limit",
            "1",
            "--include-paths",
            "--format",
            "json",
        ],
    )
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["rule"]
    assert data[0]["count"] >= 1
    assert "paths" in data[0]


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
    default_selection = _normalise_modes_cli(None)
    assert default_selection == (False, True, True)

    current_only = _normalise_modes_cli(["current"])
    assert current_only == (True, True, False)

    with pytest.raises(SystemExit):
        consume(_normalise_modes_cli(["unknown"]))

    assert normalise_modes(None) == []
    assert normalise_modes(["current", "full"]) == [Mode.CURRENT, Mode.FULL]


def test_write_config_template(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "typewiz.toml"
    consume(target.write_text("original", encoding="utf-8"))
    result = _write_config_template(target, force=False)
    assert result == 1
    assert target.read_text(encoding="utf-8") == "original"
    output = capsys.readouterr().out
    assert "[typewiz] Refusing to overwrite" in output

    result_force = _write_config_template(target, force=True)
    assert result_force == 0
    assert "[typewiz] Wrote starter config" in capsys.readouterr().out
    assert "[audit]" in target.read_text(encoding="utf-8")


def test_print_readiness_summary_variants(capsys: pytest.CaptureFixture[str]) -> None:
    summary = _empty_summary()
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

    _print_readiness_summary(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=[ReadinessStatus.BLOCKED, ReadinessStatus.CLOSE],
        limit=5,
    )
    output_folder = capsys.readouterr().out
    assert "[typewiz] readiness folder status=blocked" in output_folder
    assert "pkg: 2" in output_folder
    assert "<none>" in output_folder

    _print_readiness_summary(
        summary,
        level=ReadinessLevel.FILE,
        statuses=[ReadinessStatus.READY, ReadinessStatus.BLOCKED],
        limit=1,
    )
    output_file = capsys.readouterr().out
    assert "pkg/module.py: 0" in output_file
    assert "pkg/other.py: 3" in output_file

    _print_readiness_summary(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=None,
        limit=0,
    )
    fallback_output = capsys.readouterr().out
    assert "[typewiz] readiness folder status=blocked" in fallback_output


def test_query_readiness_invalid_data_raises() -> None:
    summary = _empty_summary()
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
            _query_readiness(
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

    _print_summary(
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

    _print_summary([run_present], [SummaryField.OVERRIDES], SummaryStyle.COMPACT)
    compact_out = capsys.readouterr().out
    assert "overrides" in compact_out
    assert "pyright:full exit=0" in compact_out


def test_cli_manifest_validate_accepts_minimal_payload(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    consume(
        manifest_path.write_text(
            json.dumps({"schemaVersion": CURRENT_MANIFEST_VERSION, "runs": []}),
            encoding="utf-8",
        ),
    )

    exit_code = main(["manifest", "validate", str(manifest_path)])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "manifest is valid" in output


def test_cli_manifest_schema_command(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    exit_code = main(["manifest", "schema", "--output", str(schema_path), "--indent", "4"])
    assert exit_code == 0
    assert schema_path.exists()
    schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema_data.get("title") == "ManifestModel"
