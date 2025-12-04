# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from typewiz import AuditConfig, Config, run_audit
from typewiz._internal.utils import consume
from typewiz.api import (
    build_summary as api_build_summary,
)
from typewiz.api import (
    render_dashboard_summary,
    validate_manifest_file,
)
from typewiz.api import (
    render_html as api_render_html,
)
from typewiz.api import (
    render_markdown as api_render_markdown,
)
from typewiz.config import EngineProfile, EngineSettings
from typewiz.core.model_types import (
    DashboardFormat,
    DashboardView,
    Mode,
    ReadinessStatus,
    SeverityLevel,
)
from typewiz.core.type_aliases import EngineName, ProfileName, RunnerName, ToolName
from typewiz.core.types import Diagnostic, RunResult
from typewiz.engines.base import EngineContext, EngineResult
from typewiz.manifest.typed import ManifestData, ToolSummary
from typewiz.manifest.versioning import CURRENT_MANIFEST_VERSION

STUB_TOOL = ToolName("stub")


class StubEngine:
    def __init__(self, result: RunResult) -> None:
        super().__init__()
        self.name = "stub"
        self._result = result

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        if context.mode is Mode.CURRENT:
            return EngineResult(
                engine=STUB_TOOL,
                mode=context.mode,
                command=["stub", "current"],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )
        return EngineResult(
            engine=STUB_TOOL,
            mode=context.mode,
            command=list(self._result.command),
            exit_code=self._result.exit_code,
            duration_ms=self._result.duration_ms,
            diagnostics=list(self._result.diagnostics),
            tool_summary=(
                cast(ToolSummary, dict(self._result.tool_summary))
                if self._result.tool_summary is not None
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
            tool=STUB_TOOL,
            severity=SeverityLevel.ERROR,
            path=tmp_path / "pkg" / "module.py",
            line=1,
            column=1,
            code="reportGeneralTypeIssues",
            message="problem",
            raw={},
        ),
    ]
    return RunResult(
        tool=STUB_TOOL,
        mode=Mode.FULL,
        command=["stub"],
        exit_code=1,
        duration_ms=5.0,
        diagnostics=diagnostics,
        tool_summary=ToolSummary(errors=1, warnings=0, information=0, total=1),
    )


def test_run_audit_programmatic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_run_result: RunResult,
) -> None:
    def _resolve_stub(_: Sequence[str]) -> list[StubEngine]:
        return [StubEngine(fake_run_result)]

    monkeypatch.setattr("typewiz.engines.resolve_engines", _resolve_stub)
    monkeypatch.setattr("typewiz.audit.api.resolve_engines", _resolve_stub)

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8"))
    override = AuditConfig(
        full_paths=["src"],
        dashboard_json=tmp_path / "summary.json",
        runners=[STUB_RUNNER],
    )

    result = run_audit(
        project_root=tmp_path,
        override=override,
        full_paths=["src"],
        build_summary_output=True,
    )

    assert result.summary is not None
    summary = result.summary
    assert summary["topFolders"]
    assert result.error_count == 1
    assert (tmp_path / "summary.json").exists()
    full_run = next(run for run in result.runs if run.mode is Mode.FULL)
    assert full_run.category_mapping == {"unknownChecks": ["reportGeneralTypeIssues"]}
    assert full_run.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    manifest = result.manifest
    assert "runs" in manifest
    manifest_runs = manifest["runs"]
    manifest_full_run = next(run for run in manifest_runs if run["mode"] == "full")
    engine_options = manifest_full_run["engineOptions"]
    assert "categoryMapping" in engine_options
    assert engine_options["categoryMapping"] == {"unknownChecks": ["reportGeneralTypeIssues"]}
    assert "toolSummary" in manifest_full_run
    assert manifest_full_run["toolSummary"] == {
        "errors": 1,
        "warnings": 0,
        "information": 0,
        "total": 1,
    }
    summary_payload = manifest_full_run["summary"]
    assert "categoryCounts" in summary_payload
    assert summary_payload["categoryCounts"].get("unknownChecks") == 1
    readiness = summary["tabs"]["readiness"]
    assert "options" in readiness
    readiness_options = readiness["options"]
    assert "unknownChecks" in readiness_options
    unknown_checks = readiness_options["unknownChecks"]
    buckets = unknown_checks.get("buckets", {})
    assert ReadinessStatus.CLOSE in buckets
    unknown_close_entries = buckets.get(ReadinessStatus.CLOSE, ())
    counts = [entry["count"] for entry in unknown_close_entries if "count" in entry]
    assert counts and sum(counts) >= 1


def test_run_audit_applies_engine_profiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class RecordingEngine:
        name = "stub"

        def __init__(self) -> None:
            super().__init__()
            self.invocations: list[tuple[str, list[str], list[str], str | None]] = []

        def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
            self.invocations.append(
                (
                    context.mode,
                    list(context.engine_options.plugin_args),
                    list(paths),
                    context.engine_options.profile,
                ),
            )
            return EngineResult(
                engine=ToolName(self.name),
                mode=context.mode,
                command=["stub", str(context.mode)],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )

        def category_mapping(self) -> dict[str, list[str]]:
            return {}

        def fingerprint_targets(
            self,
            context: EngineContext,
            paths: Sequence[str],
        ) -> Sequence[str]:
            return []

    engine = RecordingEngine()

    def _resolve_recording(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("typewiz.engines.resolve_engines", _resolve_recording)
    monkeypatch.setattr("typewiz.audit.api.resolve_engines", _resolve_recording)
    # ensure compatibility with new API method
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "extra").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8"))

    profile = EngineProfile(plugin_args=["--strict"], include=["extra"], exclude=[])
    settings = EngineSettings(plugin_args=["--engine"], profiles={STRICT_PROFILE: profile})
    config = Config(
        audit=AuditConfig(
            full_paths=["src"],
            plugin_args={STUB: ["--base"]},
            engine_settings={STUB: settings},
            active_profiles={STUB: STRICT_PROFILE},
            runners=[STUB_RUNNER],
        ),
    )

    result = run_audit(project_root=tmp_path, config=config, build_summary_output=False)

    assert len(engine.invocations) == 2
    modes = {mode for mode, _, _, _ in engine.invocations}
    assert modes == {Mode.CURRENT, Mode.FULL}
    full_invocation = next(entry for entry in engine.invocations if entry[0] is Mode.FULL)
    _, args, paths, profile_name = full_invocation
    assert args == ["--base", "--engine", "--strict"]
    assert sorted(paths) == ["extra", "src"]
    assert profile_name == STRICT_PROFILE

    assert {run.profile for run in result.runs} == {STRICT_PROFILE}
    assert all(run.plugin_args == ["--base", "--engine", "--strict"] for run in result.runs)
    assert all(run.include == ["extra"] for run in result.runs)
    manifest = result.manifest
    assert "runs" in manifest
    manifest_runs = manifest["runs"]
    run_payload = manifest_runs[0]
    engine_options = run_payload["engineOptions"]
    assert "profile" in engine_options and engine_options["profile"] == "strict"
    assert "include" in engine_options and engine_options["include"] == ["extra"]


def test_run_audit_respects_folder_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class RecordingEngine:
        name = "stub"

        def __init__(self) -> None:
            super().__init__()
            self.invocations: list[EngineContext] = []

        def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
            self.invocations.append(context)
            return EngineResult(
                engine=ToolName(self.name),
                mode=context.mode,
                command=["stub", context.mode],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )

        def category_mapping(self) -> dict[str, list[str]]:
            return {}

        def fingerprint_targets(
            self,
            context: EngineContext,
            paths: Sequence[str],
        ) -> Sequence[str]:
            return []

    engine = RecordingEngine()

    def _resolve_folder(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("typewiz.engines.resolve_engines", _resolve_folder)
    monkeypatch.setattr("typewiz.audit.api.resolve_engines", _resolve_folder)

    root_config = tmp_path / "typewiz.toml"
    consume(
        root_config.write_text(
            """
config_version = 0

[audit]
full_paths = ["packages"]
runners = ["stub"]
""",
            encoding="utf-8",
        ),
    )

    packages = tmp_path / "packages"
    billing = packages / "billing"
    billing.mkdir(parents=True, exist_ok=True)
    consume((billing / "module.py").write_text("x = 1\n", encoding="utf-8"))
    override = billing / "typewiz.dir.toml"
    consume(
        override.write_text(
            """
[active_profiles]
stub = "strict"

[engines.stub]
plugin_args = ["--billing"]
exclude = ["legacy"]
""",
            encoding="utf-8",
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = run_audit(project_root=tmp_path, config=None, build_summary_output=False)

    assert engine.invocations
    full_context = next(ctx for ctx in engine.invocations if ctx.mode is Mode.FULL)
    assert full_context.engine_options.profile == "strict"
    assert "--billing" in full_context.engine_options.plugin_args
    assert any("packages/billing" in path for path in full_context.engine_options.include)
    assert any("packages/billing/legacy" in path for path in full_context.engine_options.exclude)

    manifest = result.manifest
    assert "runs" in manifest
    manifest_runs = manifest["runs"]
    run_payload = next(run for run in manifest_runs if run["mode"] == "full")
    engine_options = run_payload["engineOptions"]
    assert "profile" in engine_options and engine_options["profile"] == "strict"
    assert "pluginArgs" in engine_options and "--billing" in engine_options["pluginArgs"]
    overrides = engine_options.get("overrides", [])
    assert overrides
    first_override = overrides[0]
    assert "path" in first_override and first_override["path"].endswith("packages/billing")
    assert first_override.get("profile") == "strict"
    assert "--billing" in first_override.get("pluginArgs", [])


def test_run_audit_cache_preserves_tool_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    diagnostics = [
        Diagnostic(
            tool=STUB_TOOL,
            severity=SeverityLevel.ERROR,
            path=tmp_path / "pkg" / "module.py",
            line=1,
            column=1,
            code="E001",
            message="failure",
            raw={},
        ),
    ]

    class RecordingEngine:
        name = "stub"

        def __init__(self) -> None:
            super().__init__()
            self.invocations: list[Mode] = []

        def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
            self.invocations.append(context.mode)
            return EngineResult(
                engine=ToolName(self.name),
                mode=context.mode,
                command=["stub", str(context.mode)],
                exit_code=1 if context.mode is Mode.FULL else 0,
                duration_ms=0.5,
                diagnostics=list(diagnostics),
                tool_summary=(
                    {"errors": 1, "warnings": 0, "information": 0, "total": 1}
                    if context.mode is Mode.FULL
                    else None
                ),
            )

        def category_mapping(self) -> dict[str, list[str]]:
            return {}

        def fingerprint_targets(
            self,
            context: EngineContext,
            paths: Sequence[str],
        ) -> Sequence[str]:
            return []

    engine = RecordingEngine()

    def _resolve_cache(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("typewiz.engines.resolve_engines", _resolve_cache)
    monkeypatch.setattr("typewiz.audit.api.resolve_engines", _resolve_cache)

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8"))

    override = AuditConfig(full_paths=["pkg"], runners=[STUB_RUNNER])

    first = run_audit(project_root=tmp_path, override=override, build_summary_output=False)
    assert engine.invocations.count(Mode.FULL) == 1
    first_full = next(run for run in first.runs if run.mode is Mode.FULL)
    assert first_full.cached is False
    assert first_full.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    cache_path = tmp_path / ".typewiz_cache" / "cache.json"
    assert cache_path.exists()
    assert not (tmp_path / ".typewiz_cache.json").exists()
    first_manifest = first.manifest
    assert "runs" in first_manifest
    first_runs = first_manifest["runs"]
    first_manifest_full = next(run for run in first_runs if run["mode"] == "full")
    assert "toolSummary" in first_manifest_full
    tool_summary = first_manifest_full["toolSummary"]
    assert "total" in tool_summary and tool_summary["total"] == 1

    second = run_audit(project_root=tmp_path, override=override, build_summary_output=False)
    # cache hit should avoid new invocations
    assert engine.invocations.count(Mode.FULL) == 1
    cached_full = next(run for run in second.runs if run.mode is Mode.FULL)
    assert cached_full.cached is True
    assert cached_full.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    second_manifest = second.manifest
    assert "runs" in second_manifest
    second_runs = second_manifest["runs"]
    cached_manifest_full = next(run for run in second_runs if run["mode"] == "full")
    assert "toolSummary" in cached_manifest_full
    cached_tool_summary = cached_manifest_full["toolSummary"]
    assert "errors" in cached_tool_summary and cached_tool_summary["errors"] == 1


def test_api_exposes_dashboard_and_manifest_helpers(tmp_path: Path) -> None:
    manifest: ManifestData = {
        "projectRoot": str(tmp_path),
        "generatedAt": "now",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    summary = api_build_summary(manifest)
    markdown = api_render_markdown(summary)
    assert isinstance(markdown, str) and markdown
    html = api_render_html(summary)
    assert "<html" in html.lower()
    rendered = render_dashboard_summary(
        summary,
        format=DashboardFormat.JSON,
        default_view=DashboardView.OVERVIEW,
    )
    assert '"tabs"' in rendered

    manifest_path = tmp_path / "manifest.json"
    _ = manifest_path.write_text(
        f'{{"schemaVersion": "{CURRENT_MANIFEST_VERSION}", "runs": []}}',
        encoding="utf-8",
    )
    validation = validate_manifest_file(manifest_path)
    assert validation.is_valid


STUB = EngineName("stub")
STUB_RUNNER = RunnerName(STUB)
STRICT_PROFILE = ProfileName("strict")
