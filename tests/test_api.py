from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from typewiz import AuditConfig, Config, run_audit
from typewiz.config import EngineProfile, EngineSettings
from typewiz.engines.base import EngineContext, EngineResult
from typewiz.types import Diagnostic, RunResult


class StubEngine:
    def __init__(self, result: RunResult) -> None:
        self.name = "stub"
        self._result = result

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        if context.mode == "current":
            return EngineResult(
                engine=self.name,
                mode=context.mode,
                command=["stub", "current"],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )
        return EngineResult(
            engine=self.name,
            mode=context.mode,
            command=list(self._result.command),
            exit_code=self._result.exit_code,
            duration_ms=self._result.duration_ms,
            diagnostics=list(self._result.diagnostics),
            tool_summary=(
                dict(self._result.tool_summary)
                if isinstance(self._result.tool_summary, dict)
                else None
            ),
        )

    def category_mapping(self) -> dict[str, list[str]]:
        return {"unknownChecks": ["reportGeneralTypeIssues"]}

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        return []


@pytest.fixture
def fake_run_result(tmp_path: Path) -> RunResult:
    (tmp_path / "pkg").mkdir(exist_ok=True)
    diagnostics = [
        Diagnostic(
            tool="stub",
            severity="error",
            path=tmp_path / "pkg" / "module.py",
            line=1,
            column=1,
            code="reportGeneralTypeIssues",
            message="problem",
            raw={},
        )
    ]
    return RunResult(
        tool="stub",
        mode="full",
        command=["stub"],
        exit_code=1,
        duration_ms=5.0,
        diagnostics=diagnostics,
        tool_summary={"errors": 1, "warnings": 0, "information": 0, "total": 1},
    )


def test_run_audit_programmatic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run_result: RunResult
) -> None:
    monkeypatch.setattr(
        "typewiz.engines.resolve_engines", lambda names: [StubEngine(fake_run_result)]
    )
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [StubEngine(fake_run_result)])

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")
    override = AuditConfig(
        full_paths=["src"], dashboard_json=tmp_path / "summary.json", runners=["stub"]
    )

    result = run_audit(
        project_root=tmp_path, override=override, full_paths=["src"], build_summary_output=True
    )

    assert result.summary is not None
    assert result.summary["topFolders"]
    assert result.error_count == 1
    assert (tmp_path / "summary.json").exists()
    full_run = next(run for run in result.runs if run.mode == "full")
    assert full_run.category_mapping == {"unknownChecks": ["reportGeneralTypeIssues"]}
    assert full_run.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    manifest_full_run = next(run for run in result.manifest["runs"] if run["mode"] == "full")
    assert manifest_full_run["engineOptions"]["categoryMapping"] == {
        "unknownChecks": ["reportGeneralTypeIssues"]
    }
    assert manifest_full_run["toolSummary"] == {
        "errors": 1,
        "warnings": 0,
        "information": 0,
        "total": 1,
    }
    assert manifest_full_run["summary"]["categoryCounts"].get("unknownChecks") == 1
    readiness = result.summary["tabs"]["readiness"]
    unknown_close_entries = readiness["options"]["unknownChecks"]["close"]
    assert unknown_close_entries
    assert sum(entry["count"] for entry in unknown_close_entries) >= 1


def test_run_audit_applies_engine_profiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class RecordingEngine:
        name = "stub"

        def __init__(self) -> None:
            self.invocations: list[tuple[str, list[str], list[str], str | None]] = []

        def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
            self.invocations.append(
                (
                    context.mode,
                    list(context.engine_options.plugin_args),
                    list(paths),
                    context.engine_options.profile,
                )
            )
            return EngineResult(
                engine=self.name,
                mode=context.mode,
                command=["stub", context.mode],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )

        def category_mapping(self) -> dict[str, list[str]]:
            return {}

        def fingerprint_targets(
            self, context: EngineContext, paths: Sequence[str]
        ) -> Sequence[str]:
            return []

    engine = RecordingEngine()
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])
    # ensure compatibility with new API method
    if not hasattr(engine, "category_mapping"):
        engine.category_mapping = lambda: {}

    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "extra").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    profile = EngineProfile(plugin_args=["--strict"], include=["extra"], exclude=[])
    settings = EngineSettings(plugin_args=["--engine"], profiles={"strict": profile})
    config = Config(
        audit=AuditConfig(
            full_paths=["src"],
            plugin_args={"stub": ["--base"]},
            engine_settings={"stub": settings},
            active_profiles={"stub": "strict"},
            runners=["stub"],
        )
    )

    result = run_audit(project_root=tmp_path, config=config, build_summary_output=False)

    assert len(engine.invocations) == 2
    modes = {mode for mode, _, _, _ in engine.invocations}
    assert modes == {"current", "full"}
    full_invocation = next(entry for entry in engine.invocations if entry[0] == "full")
    _, args, paths, profile_name = full_invocation
    assert args == ["--base", "--engine", "--strict"]
    assert sorted(paths) == ["extra", "src"]
    assert profile_name == "strict"

    assert {run.profile for run in result.runs} == {"strict"}
    assert all(run.plugin_args == ["--base", "--engine", "--strict"] for run in result.runs)
    assert all(run.include == ["extra"] for run in result.runs)
    run_payload = result.manifest["runs"][0]
    assert run_payload["engineOptions"]["profile"] == "strict"
    assert run_payload["engineOptions"]["include"] == ["extra"]


def test_run_audit_respects_folder_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class RecordingEngine:
        name = "stub"

        def __init__(self) -> None:
            self.invocations: list[EngineContext] = []

        def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
            self.invocations.append(context)
            return EngineResult(
                engine=self.name,
                mode=context.mode,
                command=["stub", context.mode],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )

        def category_mapping(self) -> dict[str, list[str]]:
            return {}

        def fingerprint_targets(
            self, context: EngineContext, paths: Sequence[str]
        ) -> Sequence[str]:
            return []

    engine = RecordingEngine()
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

    root_config = tmp_path / "typewiz.toml"
    root_config.write_text(
        """
config_version = 0

[audit]
full_paths = ["packages"]
runners = ["stub"]
""",
        encoding="utf-8",
    )

    packages = tmp_path / "packages"
    billing = packages / "billing"
    billing.mkdir(parents=True, exist_ok=True)
    (billing / "module.py").write_text("x = 1\n", encoding="utf-8")
    override = billing / "typewiz.dir.toml"
    override.write_text(
        """
[active_profiles]
stub = "strict"

[engines.stub]
plugin_args = ["--billing"]
exclude = ["legacy"]
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    result = run_audit(project_root=tmp_path, config=None, build_summary_output=False)

    assert engine.invocations
    full_context = next(ctx for ctx in engine.invocations if ctx.mode == "full")
    assert full_context.engine_options.profile == "strict"
    assert "--billing" in full_context.engine_options.plugin_args
    assert any("packages/billing" in path for path in full_context.engine_options.include)
    assert any("packages/billing/legacy" in path for path in full_context.engine_options.exclude)

    run_payload = next(run for run in result.manifest["runs"] if run["mode"] == "full")
    assert run_payload["engineOptions"]["profile"] == "strict"
    assert "--billing" in run_payload["engineOptions"]["pluginArgs"]
    overrides = run_payload["engineOptions"].get("overrides", [])
    assert overrides
    first_override = overrides[0]
    assert first_override["path"].endswith("packages/billing")
    assert first_override.get("profile") == "strict"
    assert "--billing" in first_override.get("pluginArgs", [])


def test_run_audit_cache_preserves_tool_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    diagnostics = [
        Diagnostic(
            tool="stub",
            severity="error",
            path=tmp_path / "pkg" / "module.py",
            line=1,
            column=1,
            code="E001",
            message="failure",
            raw={},
        )
    ]

    class RecordingEngine:
        name = "stub"

        def __init__(self) -> None:
            self.invocations: list[str] = []

        def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
            self.invocations.append(context.mode)
            return EngineResult(
                engine=self.name,
                mode=context.mode,
                command=["stub", context.mode],
                exit_code=1 if context.mode == "full" else 0,
                duration_ms=0.5,
                diagnostics=list(diagnostics),
                tool_summary=(
                    {"errors": 1, "warnings": 0, "information": 0, "total": 1}
                    if context.mode == "full"
                    else None
                ),
            )

        def category_mapping(self) -> dict[str, list[str]]:
            return {}

        def fingerprint_targets(
            self, context: EngineContext, paths: Sequence[str]
        ) -> Sequence[str]:
            return []

    engine = RecordingEngine()
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8")

    override = AuditConfig(full_paths=["pkg"], runners=["stub"])

    first = run_audit(project_root=tmp_path, override=override, build_summary_output=False)
    assert engine.invocations.count("full") == 1
    first_full = next(run for run in first.runs if run.mode == "full")
    assert first_full.cached is False
    assert first_full.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    first_manifest_full = next(run for run in first.manifest["runs"] if run["mode"] == "full")
    assert first_manifest_full["toolSummary"]["total"] == 1

    second = run_audit(project_root=tmp_path, override=override, build_summary_output=False)
    # cache hit should avoid new invocations
    assert engine.invocations.count("full") == 1
    cached_full = next(run for run in second.runs if run.mode == "full")
    assert cached_full.cached is True
    assert cached_full.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    cached_manifest_full = next(run for run in second.manifest["runs"] if run["mode"] == "full")
    assert cached_manifest_full["toolSummary"]["errors"] == 1
