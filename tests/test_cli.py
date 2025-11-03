from __future__ import annotations

import json
import sys
import types
from collections.abc import Sequence
from pathlib import Path

import pytest

from typewiz.api import AuditResult
from typewiz.cli import (
    SUMMARY_FIELD_CHOICES,
    _collect_plugin_args,
    _collect_profile_args,
    _normalise_modes,
    _parse_summary_fields,
    _print_readiness_summary,
    _print_summary,
    _write_config_template,
    main,
)
from typewiz.config import Config
from typewiz.engines.base import EngineContext, EngineResult
from typewiz.summary_types import SummaryData
from typewiz.types import Diagnostic, RunResult


class StubEngine:
    def __init__(self, result: RunResult, expected_profile: str | None = None) -> None:
        self.name = "stub"
        self._result = result
        self.expected_profile = expected_profile
        self.invocations: list[tuple[str, list[str], list[str]]] = []

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        if self.expected_profile is not None:
            assert context.engine_options.profile == self.expected_profile
        self.invocations.append(
            (context.mode, list(context.engine_options.plugin_args), list(paths))
        )
        if context.mode == "full":
            return EngineResult(
                engine=self.name,
                mode=context.mode,
                command=["stub", *paths],
                exit_code=0,
                duration_ms=0.2,
                diagnostics=[],
            )
        return EngineResult(
            engine=self.name,
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


@pytest.fixture
def fake_run(tmp_path: Path) -> RunResult:
    (tmp_path / "pkg").mkdir(exist_ok=True)
    diag = Diagnostic(
        tool="stub",
        severity="error",
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="reportGeneralTypeIssues",
        message="oops",
        raw={},
    )
    return RunResult(
        tool="stub",
        mode="current",
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
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    dashboard_path = tmp_path / "dashboard.md"
    dashboard_path.write_text("stale", encoding="utf-8")
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
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2  # fail on warnings triggered (error counts)
    assert manifest_path.exists()
    assert dashboard_path.exists()
    assert dashboard_path.read_text(encoding="utf-8") != "stale"
    assert any(mode == "full" for mode, _, _ in engine.invocations)
    assert all("--cli-flag" in args for _, args, _ in engine.invocations)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_entry = manifest["runs"][0]
    assert run_entry["engineOptions"]["profile"] == "strict"
    assert run_entry["engineOptions"]["pluginArgs"] == ["--cli-flag"]
    assert "profile=" not in captured.out


def test_cli_dashboard_output(tmp_path: Path) -> None:
    manifest = {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": str(tmp_path),
        "runs": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    exit_code = main(
        [
            "dashboard",
            "--manifest",
            str(manifest_path),
            "--format",
            "json",
        ]
    )
    assert exit_code == 0


def test_cli_audit_readiness_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run: RunResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = StubEngine(fake_run)
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")

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
        ]
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
        ]
    )
    assert exit_code_readiness == 0
    readiness_output = capsys.readouterr().out
    assert "[typewiz] readiness file status=blocked" in readiness_output


def test_cli_summary_extras(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run: RunResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = StubEngine(fake_run, expected_profile="strict")
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "extras").mkdir(exist_ok=True)
    config_path = tmp_path / "typewiz.toml"
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
    )
    override_path = tmp_path / "extras" / "typewiz.dir.toml"
    override_path.write_text(
        """
[active_profiles]
stub = "strict"

[engines.stub]
plugin_args = ["--extras"]
exclude = ["unused"]
""",
        encoding="utf-8",
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
        ]
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


def test_cli_mode_only_full(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run: RunResult
) -> None:
    engine = StubEngine(fake_run)
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

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
        ]
    )

    assert exit_code == 0
    assert engine.invocations == [("full", [], ["pkg"])]


def test_cli_plugin_arg_validation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = StubEngine(
        RunResult(
            tool="stub",
            mode="current",
            command=["stub"],
            exit_code=0,
            duration_ms=0.0,
            diagnostics=[],
        )
    )
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

    with pytest.raises(SystemExit):
        main(
            [
                "audit",
                "--runner",
                "stub",
                "--project-root",
                str(tmp_path),
                "--plugin-arg",
                "stub",
            ]
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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run: RunResult
) -> None:
    engine = StubEngine(fake_run)
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])
    monkeypatch.chdir(tmp_path)

    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8")

    exit_code = main(
        [
            "audit",
            "--runner",
            "stub",
            "pkg",
        ]
    )

    assert exit_code == 0
    # Fallback root detection should still run both modes
    assert {mode for mode, *_ in engine.invocations} == {"current", "full"}


def test_cli_audit_requires_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = Config()
    monkeypatch.setattr("typewiz.cli.load_config", lambda path: cfg)
    monkeypatch.setattr("typewiz.cli.default_full_paths", lambda root: [])

    with pytest.raises(SystemExit):
        main(["audit"])


def test_cli_audit_full_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = Config()
    cfg.audit.runners = ["pyright"]

    summary: SummaryData = {
        "tabs": {
            "overview": {
                "severityTotals": {
                    "error": 0,
                    "warning": 0,
                    "information": 1,
                }
            }
        }
    }
    prev_summary: SummaryData = {
        "tabs": {
            "overview": {
                "severityTotals": {
                    "error": 0,
                    "warning": 0,
                    "information": 0,
                }
            }
        }
    }

    diag = Diagnostic(
        tool="pyright",
        severity="information",
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="information",
        message="info",
    )
    run = RunResult(
        tool="pyright",
        mode="current",
        command=["pyright", "pkg"],
        exit_code=0,
        duration_ms=1.0,
        diagnostics=[diag],
        profile="strict",
        config_file=tmp_path / "pyrightconfig.json",
        plugin_args=["--strict"],
        include=["pkg"],
        exclude=[],
        overrides=[{"path": "pkg", "profile": "strict"}],
        scanned_paths=["pkg"],
    )
    audit_result = AuditResult(
        manifest={"runs": []},
        runs=[run],
        summary=summary,
        error_count=0,
        warning_count=0,
    )

    monkeypatch.setattr("typewiz.cli.load_config", lambda path: cfg)
    monkeypatch.setattr("typewiz.cli.resolve_project_root", lambda path: tmp_path)
    monkeypatch.setattr("typewiz.cli.default_full_paths", lambda root: ["pkg"])
    monkeypatch.setattr("typewiz.cli.run_audit", lambda **_: audit_result)
    monkeypatch.setattr("typewiz.cli.render_markdown", lambda data: "markdown")
    monkeypatch.setattr("typewiz.cli.render_html", lambda data, default_view: "<html>")

    def _fake_build_summary(data: object) -> SummaryData:
        if isinstance(data, dict) and data.get("__prev__"):
            return prev_summary
        return summary

    monkeypatch.setattr("typewiz.cli.build_summary", _fake_build_summary)
    monkeypatch.setattr(
        "typewiz.dashboard.load_manifest",
        lambda path: {"__prev__": True},
    )

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    compare_path = tmp_path / "prev_manifest.json"
    compare_path.write_text("{}", encoding="utf-8")

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
        ]
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
    manifest_path.write_text(json.dumps({"runs": []}), encoding="utf-8")

    summary: SummaryData = {"tabs": {}}
    monkeypatch.setattr("typewiz.cli.build_summary", lambda data: summary)
    monkeypatch.setattr("typewiz.cli.render_markdown", lambda data: "markdown")
    monkeypatch.setattr("typewiz.cli.render_html", lambda data, default_view: "<html>")

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
        ]
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
        ]
    )
    assert exit_code_html == 0
    assert html_path.read_text(encoding="utf-8") == "<html>"


def test_cli_manifest_validate_with_jsonschema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"generatedAt": "now", "projectRoot": ".", "runs": []}), encoding="utf-8"
    )
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    class DummyValidator:
        def __init__(self, schema: object) -> None:
            self.schema = schema

        def iter_errors(self, data: object) -> list[object]:
            return []

    dummy_module = types.SimpleNamespace(Draft7Validator=DummyValidator)
    monkeypatch.setitem(sys.modules, "jsonschema", dummy_module)

    exit_code = main(["manifest", "validate", str(manifest_path), "--schema", str(schema_path)])
    assert exit_code == 0
    assert "manifest is valid" in capsys.readouterr().out


def test_cli_manifest_validate_runs_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = tmp_path / "bad.json"
    manifest_path.write_text(
        json.dumps({"generatedAt": "now", "projectRoot": ".", "runs": {}}), encoding="utf-8"
    )
    import importlib

    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
    )

    exit_code = main(["manifest", "validate", str(manifest_path)])
    assert exit_code == 2
    assert "manifest.runs must be an array" in capsys.readouterr().out


def test_cli_manifest_unknown_action(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_cmd = ["manifest", "unknown"]
    with pytest.raises(SystemExit):
        main(manifest_cmd)


def test_parse_summary_fields_variants() -> None:
    fields = _parse_summary_fields(" profile , , plugin-args ")
    assert fields == ["profile", "plugin-args"]

    all_fields = _parse_summary_fields("all")
    assert all_fields == sorted(SUMMARY_FIELD_CHOICES)

    with pytest.raises(SystemExit):
        _parse_summary_fields("profile,unknown")


def test_collect_plugin_args_variants() -> None:
    result = _collect_plugin_args(["pyright=--strict", "pyright:--warnings", "mypy = --strict "])
    assert result == {"pyright": ["--strict", "--warnings"], "mypy": ["--strict"]}

    with pytest.raises(SystemExit):
        _collect_plugin_args(["pyright"])
    with pytest.raises(SystemExit):
        _collect_plugin_args(["=--oops"])
    with pytest.raises(SystemExit):
        _collect_plugin_args(["pyright="])


def test_collect_profile_args_variants() -> None:
    profiles = _collect_profile_args([("pyright", "strict"), ["mypy", "baseline"]])
    assert profiles == {"pyright": "strict", "mypy": "baseline"}

    with pytest.raises(SystemExit):
        _collect_profile_args([("pyright",)])
    with pytest.raises(SystemExit):
        _collect_profile_args([("pyright", "")])


def test_normalise_modes_variants() -> None:
    default_selection = _normalise_modes(None)
    assert default_selection == (False, True, True)

    current_only = _normalise_modes(["current"])
    assert current_only == (True, True, False)

    with pytest.raises(SystemExit):
        _normalise_modes(["unknown"])


def test_write_config_template(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "typewiz.toml"
    target.write_text("original", encoding="utf-8")
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
    summary: SummaryData = {
        "tabs": {
            "readiness": {
                "options": {
                    "unknownChecks": {
                        "ready": [{"path": "pkg", "count": "not-a-number"}],
                        "close": [],
                        "blocked": [{"path": "pkg", "count": 2}],
                        "threshold": 0,
                    }
                },
                "strict": {
                    "ready": [{"path": "pkg/module.py", "diagnostics": 0}],
                    "blocked": [{"path": "pkg/other.py", "diagnostics": "3"}],
                },
            }
        }
    }

    _print_readiness_summary(
        summary,
        level="folder",
        statuses=["blocked", "close", "invalid"],
        limit=5,
    )
    output_folder = capsys.readouterr().out
    assert "[typewiz] readiness folder status=blocked" in output_folder
    assert "pkg: 2" in output_folder
    assert "<none>" in output_folder

    _print_readiness_summary(
        summary,
        level="file",
        statuses=["ready", "blocked"],
        limit=1,
    )
    output_file = capsys.readouterr().out
    assert "pkg/module.py: 0" in output_file
    assert "pkg/other.py: 3" in output_file

    _print_readiness_summary(
        summary,
        level="folder",
        statuses=["invalid"],
        limit=0,
    )
    fallback_output = capsys.readouterr().out
    assert "[typewiz] readiness folder status=blocked" in fallback_output


def test_print_summary_styles(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    diag = Diagnostic(
        tool="pyright",
        severity="error",
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="reportGeneralTypeIssues",
        message="boom",
    )

    override_entry = {
        "path": "pkg",
        "profile": "strict",
        "pluginArgs": ["--warnings"],
        "include": ["src"],
        "exclude": ["tests"],
    }
    run_expanded = RunResult(
        tool="pyright",
        mode="current",
        command=["pyright", "--project"],
        exit_code=0,
        duration_ms=0.1,
        diagnostics=[diag],
        profile=None,
        config_file=None,
        plugin_args=["--strict"],
        include=["pkg"],
        exclude=[],
        overrides=[override_entry],
    )
    run_present = RunResult(
        tool="pyright",
        mode="full",
        command=["pyright", "."],
        exit_code=0,
        duration_ms=0.1,
        diagnostics=[],
        profile="strict",
        config_file=tmp_path / "pyrightconfig.json",
        plugin_args=[],
        include=[],
        exclude=["legacy"],
        overrides=[override_entry],
    )

    _print_summary(
        [run_expanded, run_present],
        ["profile", "config", "plugin-args", "paths", "overrides"],
        "expanded",
    )
    expanded_out = capsys.readouterr().out
    assert "override pkg" in expanded_out
    assert "profile: —" in expanded_out
    assert "config: —" in expanded_out

    _print_summary([run_present], ["overrides"], "compact")
    compact_out = capsys.readouterr().out
    assert "overrides" in compact_out
    assert "pyright:full exit=0" in compact_out


def test_cli_manifest_validate_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"generatedAt": "now", "projectRoot": ".", "runs": []}), encoding="utf-8"
    )

    import importlib

    def _raise_missing(_: str) -> None:
        raise ModuleNotFoundError("jsonschema not available")

    monkeypatch.setattr(importlib, "import_module", _raise_missing)

    exit_code = main(["manifest", "validate", str(manifest_path)])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "manifest passes basic validation" in output


def test_cli_manifest_validate_missing_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import importlib

    manifest_path = tmp_path / "invalid.json"
    manifest_path.write_text(json.dumps({"generatedAt": "now"}), encoding="utf-8")
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
    )

    exit_code = main(["manifest", "validate", str(manifest_path)])
    assert exit_code == 2
    output = capsys.readouterr().out
    assert "manifest missing required keys" in output
