from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pytest

from typewiz.cli import main
from typewiz.engines.base import EngineContext, EngineResult
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
    exit_code = main([
        "audit",
        "--runner",
        "stub",
        "--project-root",
        str(tmp_path),
        "--full-path",
        "src",
        "--manifest",
        str(manifest_path),
        "--dashboard-markdown",
        str(dashboard_path),
        "--fail-on",
        "warnings",
        "--profile",
        "stub=strict",
        "--plugin-arg",
        "stub=--cli-flag",
        "--summary",
        "compact",
    ])

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

    exit_code = main([
        "dashboard",
        "--manifest",
        str(manifest_path),
        "--format",
        "json",
    ])
    assert exit_code == 0


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

    manifest_path = tmp_path / "manifest.json"
    dashboard_path = tmp_path / "dashboard.md"
    monkeypatch.chdir(tmp_path)
    exit_code = main([
        "audit",
        "--runner",
        "stub",
        "--full-path",
        "src",
        "--manifest",
        str(manifest_path),
        "--dashboard-markdown",
        str(dashboard_path),
        "--profile",
        "stub=strict",
        "--plugin-arg",
        "stub=--cli-flag",
        "--summary",
        "expanded",
        "--summary-fields",
        "profile,plugin-args,paths",
    ])

    assert exit_code == 0

    captured = capsys.readouterr()
    assert "- profile: strict" in captured.out
    assert "- plugin args: --cli-flag, --strict" in captured.out
    assert "- include: extras" in captured.out
    assert "- exclude: —" in captured.out
    assert "- config" not in captured.out

    # Request full summary (includes every field automatically)
    exit_code = main([
        "audit",
        "--runner",
        "stub",
        "--full-path",
        "src",
        "--manifest",
        str(manifest_path),
        "--profile",
        "stub=strict",
        "--plugin-arg",
        "stub=--cli-flag",
        "--summary",
        "full",
    ])

    assert exit_code == 0

    captured = capsys.readouterr()
    assert "- config: —" in captured.out
