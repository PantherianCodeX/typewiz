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

"""Integration tests for Workflows CLI Workflows."""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import pytest

from ratchetr._internal.utils import consume
from ratchetr.api import AuditResult
from ratchetr.cli.app import main
from ratchetr.config import Config
from ratchetr.core.model_types import (
    DashboardFormat,
    DashboardView,
    Mode,
    OverrideEntry,
    SeverityLevel,
)
from ratchetr.core.type_aliases import EngineName, RelPath, RunnerName, ToolName
from ratchetr.core.types import Diagnostic, RunResult
from ratchetr.manifest.versioning import CURRENT_MANIFEST_VERSION
from tests.fixtures.builders import build_cli_manifest, build_empty_summary
from tests.fixtures.stubs import StubEngine

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from ratchetr.core.summary_types import SummaryData

pytestmark = [pytest.mark.integration, pytest.mark.cli]

STUB_TOOL = ToolName("stub")
PYRIGHT_ENGINE = EngineName("pyright")
PYRIGHT_RUNNER = RunnerName(PYRIGHT_ENGINE)
PYRIGHT_TOOL = ToolName("pyright")


@dataclass(slots=True)
class AuditFullOutputsContext:
    """Container for paths produced by the full audit workflow."""

    compare_path: Path
    dashboard_json: Path
    dashboard_md: Path
    dashboard_html: Path


def _patch_engine_resolution(monkeypatch: pytest.MonkeyPatch, engine: StubEngine) -> None:
    def _resolve(_: Sequence[str]) -> list[StubEngine]:
        return [engine]

    monkeypatch.setattr("ratchetr.engines.resolve_engines", _resolve)
    monkeypatch.setattr("ratchetr.audit.api.resolve_engines", _resolve)


def _run_cli_command(args: Sequence[str]) -> int:
    """Invoke the CLI entrypoint with the provided arguments.

    Returns:
        Integer exit code returned by the CLI.
    """
    return main(list(args))


def _make_dashboard_renderer(
    summary: SummaryData,
    *,
    allowed_views: set[str],
) -> Callable[..., str]:
    """Return a renderer that mimics ``render_dashboard_summary``."""

    def _render_dashboard(summary_arg: SummaryData, **kwargs: object) -> str:
        assert summary_arg is summary
        output_format = cast("DashboardFormat", kwargs.get("output_format"))
        default_view = cast("DashboardView | str", kwargs["default_view"])
        if output_format is DashboardFormat.JSON:
            return json.dumps(summary_arg)
        if output_format is DashboardFormat.MARKDOWN:
            return "markdown"
        view_value = default_view.value if isinstance(default_view, DashboardView) else default_view
        assert view_value in allowed_views
        return "<html>"

    return _render_dashboard


def _arrange_cli_audit_full_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> AuditFullOutputsContext:
    cfg = Config()
    cfg.audit.runners = [PYRIGHT_RUNNER]

    summary = build_empty_summary()
    summary["tabs"]["overview"]["severityTotals"] = {
        SeverityLevel.ERROR: 0,
        SeverityLevel.WARNING: 0,
        SeverityLevel.INFORMATION: 1,
    }
    prev_summary = build_empty_summary()
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

    monkeypatch.setattr("ratchetr.cli.commands.audit.load_config", _load_config)
    monkeypatch.setattr("ratchetr.cli.commands.audit.resolve_project_root", _resolve_root)
    monkeypatch.setattr("ratchetr.cli.commands.audit.default_full_paths", _default_paths)
    monkeypatch.setattr("ratchetr.cli.commands.audit.run_audit", _run_audit_stub)

    def _fake_build_summary(data: object) -> SummaryData:
        if isinstance(data, dict):
            dict_data = cast("dict[str, object]", data)
            if dict_data.get("__prev__"):
                return prev_summary
        return summary

    monkeypatch.setattr("ratchetr.cli.commands.audit.build_summary", _fake_build_summary)

    def _load_prev_summary(_: Path) -> SummaryData:
        return prev_summary

    monkeypatch.setattr(
        "ratchetr.cli.commands.audit.load_summary_from_manifest",
        _load_prev_summary,
    )

    renderer = _make_dashboard_renderer(
        summary,
        allowed_views={"engines", "overview", "hotspots", "readiness", "runs"},
    )
    monkeypatch.setattr(
        "ratchetr.services.dashboard.render_dashboard_summary",
        renderer,
    )

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    compare_path = tmp_path / "prev_manifest.json"
    consume(compare_path.write_text("{}", encoding="utf-8"))

    dashboard_json = tmp_path / "dashboard.json"
    dashboard_md = tmp_path / "dashboard.md"
    dashboard_html = tmp_path / "dashboard.html"
    return AuditFullOutputsContext(
        compare_path=compare_path,
        dashboard_json=dashboard_json,
        dashboard_md=dashboard_md,
        dashboard_html=dashboard_html,
    )


def _act_cli_audit_full_outputs(
    context: AuditFullOutputsContext,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str]:
    exit_code = _run_cli_command(
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
            str(context.compare_path),
            "--dashboard-json",
            str(context.dashboard_json),
            "--dashboard-markdown",
            str(context.dashboard_md),
            "--dashboard-html",
            str(context.dashboard_html),
            "--dashboard-view",
            "engines",
        ],
    )
    return exit_code, capsys.readouterr().out


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
    exit_code = _run_cli_command(
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

    manifest_json = cast("dict[str, object]", json.loads(manifest_path.read_text(encoding="utf-8")))
    runs_value = manifest_json.get("runs")
    assert isinstance(runs_value, list)
    assert runs_value
    first_run = cast("dict[str, object]", runs_value[0])
    engine_options_obj = cast("dict[str, object]", first_run.get("engineOptions", {}))
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

    exit_code = _run_cli_command(
        [
            "dashboard",
            "--manifest",
            str(manifest_path),
            "--format",
            "json",
        ],
    )
    assert exit_code == 0


def test_cli_version_flag(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("RATCHETR_LICENSE_KEY", "test")
    exit_code = _run_cli_command(["--version"])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ratchetr" in output.lower()


def test_cli_engines_list(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("RATCHETR_LICENSE_KEY", "test")
    exit_code = _run_cli_command(["engines", "list", "--format", "json"])
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert any(entry["name"] == "pyright" for entry in data)


def test_cli_cache_clear(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_dir = tmp_path / ".ratchetr_cache"
    cache_dir.mkdir()
    consume((cache_dir / "cache.json").write_text("{}", encoding="utf-8"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RATCHETR_LICENSE_KEY", "test")
    exit_code = _run_cli_command(["cache", "clear"])
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
    exit_code = _run_cli_command(
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
    assert "[ratchetr] readiness folder status=blocked" in captured.out
    assert "pkg" in captured.out

    exit_code_readiness = _run_cli_command(
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
    assert "[ratchetr] readiness file status=blocked" in readiness_output


def test_cli_readiness_details_and_severity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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
    config_path = tmp_path / "ratchetr.toml"
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
    override_path = tmp_path / "extras" / "ratchetr.dir.toml"
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
    exit_code = _run_cli_command(
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

    exit_code = _run_cli_command(
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
        "SummaryData",
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

    def _noop(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr("ratchetr.cli.commands.audit.run_audit", _run_audit_stub)
    monkeypatch.setattr("ratchetr.cli.commands.audit.print_summary", _noop)
    monkeypatch.setattr("ratchetr.cli.commands.audit._maybe_print_readiness", _noop)

    (tmp_path / "pkg").mkdir(exist_ok=True)
    consume((tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8"))

    exit_code = _run_cli_command(
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

    exit_code = _run_cli_command(
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

    with pytest.raises(SystemExit, match=r".*"):
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
    target = tmp_path / "ratchetr.toml"
    exit_code = _run_cli_command(["init", "--output", str(target)])
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

    exit_code = _run_cli_command(
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

    monkeypatch.setattr("ratchetr.cli.commands.audit.load_config", _load_config)
    monkeypatch.setattr("ratchetr.cli.commands.audit.default_full_paths", _default_paths)

    with pytest.raises(SystemExit, match=r".*"):
        consume(main(["audit"]))


def test_cli_audit_full_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    context = _arrange_cli_audit_full_outputs(monkeypatch, tmp_path)
    exit_code, output = _act_cli_audit_full_outputs(context, capsys)

    assert "delta: errors=0 warnings=0 info=+1" in output
    assert exit_code == 2
    assert context.dashboard_json.exists()
    assert context.dashboard_md.exists()
    assert context.dashboard_html.exists()


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

    summary = build_empty_summary()

    def _load_summary(_: Path) -> SummaryData:
        return summary

    monkeypatch.setattr(
        "ratchetr.cli.app.load_summary_from_manifest",
        _load_summary,
    )
    renderer = _make_dashboard_renderer(
        summary,
        allowed_views={"overview", "engines", "hotspots", "readiness", "runs"},
    )
    monkeypatch.setattr(
        "ratchetr.cli.app.render_dashboard_summary",
        renderer,
    )

    exit_code_json = _run_cli_command(["dashboard", "--manifest", str(manifest_path)])
    assert exit_code_json == 0
    out_json = capsys.readouterr().out
    assert json.loads(out_json) == summary

    md_path = tmp_path / "dashboard.md"
    exit_code_md = _run_cli_command(
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
    exit_code_html = _run_cli_command(
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
            self.errors: list[object] = []

        def iter_errors(self, _data: object) -> list[object]:
            return list(self.errors)

    dummy_module = types.SimpleNamespace(Draft7Validator=DummyValidator)
    monkeypatch.setitem(sys.modules, "jsonschema", dummy_module)

    exit_code = _run_cli_command(["manifest", "validate", str(manifest_path), "--schema", str(schema_path)])
    assert exit_code == 0
    assert "manifest is valid" in capsys.readouterr().out


def test_cli_manifest_validate_runs_type(
    tmp_path: Path,
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

    exit_code = _run_cli_command(["manifest", "validate", str(manifest_path)])
    assert exit_code == 2
    output = capsys.readouterr().out
    assert "validation error at runs" in output
    assert "runs must be a list" in output


def test_cli_manifest_unknown_action() -> None:
    manifest_cmd = ["manifest", "unknown"]
    with pytest.raises(SystemExit, match=r".*"):
        consume(main(manifest_cmd))


def test_cli_query_overview_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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
    exit_code_files = _run_cli_command(
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
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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
    manifest_path = build_cli_manifest(tmp_path)
    exit_code = _run_cli_command(
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

    exit_code = _run_cli_command(["manifest", "validate", str(manifest_path)])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "manifest is valid" in output


def test_cli_manifest_schema_command(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    exit_code = _run_cli_command(["manifest", "schema", "--output", str(schema_path), "--indent", "4"])
    assert exit_code == 0
    assert schema_path.exists()
    schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema_data.get("title") == "ManifestModel"
