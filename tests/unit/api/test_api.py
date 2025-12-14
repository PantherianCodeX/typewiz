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

"""Unit tests for API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ratchetr import AuditConfig, Config, run_audit
from ratchetr._internal.utils import consume
from ratchetr.api import build_summary as api_build_summary
from ratchetr.api import render_dashboard_summary, validate_manifest_file
from ratchetr.api import render_html as api_render_html
from ratchetr.api import render_markdown as api_render_markdown
from ratchetr.config import EngineProfile, EngineSettings
from ratchetr.core.model_types import (
    DashboardFormat,
    DashboardView,
    Mode,
    ReadinessStatus,
    SeverityLevel,
)
from ratchetr.core.type_aliases import EngineName, ProfileName, RunnerName, ToolName
from ratchetr.core.types import Diagnostic, RunResult
from ratchetr.manifest.typed import ManifestData, ToolSummary
from ratchetr.manifest.versioning import CURRENT_MANIFEST_VERSION
from ratchetr.services.dashboard import emit_dashboard_outputs
from tests.fixtures.stubs import AuditStubEngine, RecordingEngine

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

pytestmark = pytest.mark.unit

STUB_TOOL = ToolName("stub")


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
        mode=Mode.TARGET,
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
    def _resolve_stub(_: Sequence[str]) -> list[AuditStubEngine]:
        return [AuditStubEngine(fake_run_result)]

    monkeypatch.setattr("ratchetr.engines.resolve_engines", _resolve_stub)
    monkeypatch.setattr("ratchetr.audit.api.resolve_engines", _resolve_stub)

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8"))
    override = AuditConfig(
        include_paths=["src"],
        dashboard_json=tmp_path / "summary.json",
        runners=[STUB_RUNNER],
    )

    result = run_audit(
        project_root=tmp_path,
        override=override,
        include_paths=["src"],
        build_summary_output=True,
    )

    assert result.summary is not None
    summary = result.summary
    assert summary["topFolders"]
    assert result.error_count == 1

    emit_dashboard_outputs(
        summary,
        json_path=tmp_path / "summary.json",
        markdown_path=None,
        html_path=None,
        default_view="overview",
    )
    assert (tmp_path / "summary.json").exists()
    target_run = next(run for run in result.runs if run.mode is Mode.TARGET)
    assert target_run.category_mapping == {"unknownChecks": ["reportGeneralTypeIssues"]}
    assert target_run.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    manifest = result.manifest
    assert "runs" in manifest
    manifest_runs = manifest["runs"]
    manifest_target_run = next(run for run in manifest_runs if run["mode"] == "target")
    engine_options = manifest_target_run["engineOptions"]
    assert "categoryMapping" in engine_options
    assert engine_options["categoryMapping"] == {"unknownChecks": ["reportGeneralTypeIssues"]}
    assert "toolSummary" in manifest_target_run
    assert manifest_target_run["toolSummary"] == {
        "errors": 1,
        "warnings": 0,
        "information": 0,
        "total": 1,
    }
    summary_payload = manifest_target_run["summary"]
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
    assert counts
    assert sum(counts) >= 1


def test_run_audit_applies_engine_profiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = RecordingEngine()

    def _resolve_recording(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("ratchetr.engines.resolve_engines", _resolve_recording)
    monkeypatch.setattr("ratchetr.audit.api.resolve_engines", _resolve_recording)
    # ensure compatibility with new API method
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "extra").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8"))

    profile = EngineProfile(plugin_args=["--strict"], include=["extra"], exclude=[])
    settings = EngineSettings(plugin_args=["--engine"], profiles={STRICT_PROFILE: profile})
    config = Config(
        audit=AuditConfig(
            include_paths=["src"],
            plugin_args={STUB: ["--base"]},
            engine_settings={STUB: settings},
            active_profiles={STUB: STRICT_PROFILE},
            runners=[STUB_RUNNER],
        ),
    )

    result = run_audit(project_root=tmp_path, config=config, build_summary_output=False)

    # Per-engine deduplication: plans are equivalent (cli_paths=None), so only TARGET runs
    assert len(engine.invocations) == 1
    invocation = engine.invocations[0]
    assert invocation.mode is Mode.TARGET  # TARGET is canonical
    assert invocation.plugin_args == ["--base", "--engine", "--strict"]
    assert sorted(invocation.paths) == ["extra", "src"]
    assert invocation.profile == STRICT_PROFILE

    assert {run.profile for run in result.runs} == {STRICT_PROFILE}
    assert all(run.plugin_args == ["--base", "--engine", "--strict"] for run in result.runs)
    assert all(run.include == ["extra"] for run in result.runs)
    manifest = result.manifest
    assert "runs" in manifest
    manifest_runs = manifest["runs"]
    run_payload = manifest_runs[0]
    engine_options = run_payload["engineOptions"]
    assert "profile" in engine_options
    assert engine_options["profile"] == "strict"
    assert "include" in engine_options
    assert engine_options["include"] == ["extra"]


def test_run_audit_respects_folder_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = RecordingEngine()

    def _resolve_folder(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("ratchetr.engines.resolve_engines", _resolve_folder)
    monkeypatch.setattr("ratchetr.audit.api.resolve_engines", _resolve_folder)

    root_config = tmp_path / "ratchetr.toml"
    consume(
        root_config.write_text(
            """
config_version = 0

[audit]
include_paths = ["packages"]
runners = ["stub"]
""",
            encoding="utf-8",
        ),
    )

    packages = tmp_path / "packages"
    billing = packages / "billing"
    billing.mkdir(parents=True, exist_ok=True)
    consume((billing / "module.py").write_text("x = 1\n", encoding="utf-8"))
    override = billing / "ratchetr.dir.toml"
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
    target_invocation = next(inv for inv in engine.invocations if inv.mode is Mode.TARGET)
    target_context = target_invocation.context
    assert target_context.engine_options.profile == "strict"
    assert "--billing" in target_context.engine_options.plugin_args
    assert any("packages/billing" in path for path in target_context.engine_options.include)
    assert any("packages/billing/legacy" in path for path in target_context.engine_options.exclude)

    manifest = result.manifest
    assert "runs" in manifest
    manifest_runs = manifest["runs"]
    run_payload = next(run for run in manifest_runs if run["mode"] == "target")
    engine_options = run_payload["engineOptions"]
    assert "profile" in engine_options
    assert engine_options["profile"] == "strict"
    assert "pluginArgs" in engine_options
    assert "--billing" in engine_options["pluginArgs"]
    overrides = engine_options.get("overrides", [])
    assert overrides
    first_override = overrides[0]
    assert "path" in first_override
    assert first_override["path"].endswith("packages/billing")
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

    engine = RecordingEngine(
        diagnostics=diagnostics,
        tool_summary_on_target={"errors": 1, "warnings": 0, "information": 0, "total": 1},
        target_exit_code=1,
        current_exit_code=0,
    )

    def _resolve_cache(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("ratchetr.engines.resolve_engines", _resolve_cache)
    monkeypatch.setattr("ratchetr.audit.api.resolve_engines", _resolve_cache)

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8"))

    override = AuditConfig(include_paths=["pkg"], runners=[STUB_RUNNER])

    first = run_audit(project_root=tmp_path, override=override, build_summary_output=False)
    assert sum(1 for inv in engine.invocations if inv.mode is Mode.TARGET) == 1
    first_target = next(run for run in first.runs if run.mode is Mode.TARGET)
    assert first_target.cached is False
    assert first_target.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    cache_path = tmp_path / ".ratchetr_cache" / "cache.json"
    assert cache_path.exists()
    assert not (tmp_path / ".ratchetr_cache.json").exists()
    runs_first = first.manifest.get("runs") or []
    first_manifest_target = next(run for run in runs_first if run.get("mode") == "target")
    tool_summary = first_manifest_target.get("toolSummary") or {}
    assert tool_summary.get("total") == 1

    second = run_audit(project_root=tmp_path, override=override, build_summary_output=False)
    # cache hit should avoid new invocations
    assert sum(1 for inv in engine.invocations if inv.mode is Mode.TARGET) == 1
    cached_target = next(run for run in second.runs if run.mode is Mode.TARGET)
    assert cached_target.cached is True
    assert cached_target.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    runs_second = second.manifest.get("runs") or []
    cached_manifest_target = next(run for run in runs_second if run.get("mode") == "target")
    cached_tool_summary = cached_manifest_target.get("toolSummary") or {}
    assert cached_tool_summary.get("errors") == 1


def test_api_exposes_dashboard_and_manifest_helpers(tmp_path: Path) -> None:
    manifest: ManifestData = {
        "projectRoot": str(tmp_path),
        "generatedAt": "now",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    summary = api_build_summary(manifest)
    markdown = api_render_markdown(summary)
    assert isinstance(markdown, str)
    assert markdown
    html = api_render_html(summary)
    assert "<html" in html.lower()
    rendered = render_dashboard_summary(
        summary,
        output_format=DashboardFormat.JSON,
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
