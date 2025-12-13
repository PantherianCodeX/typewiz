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

"""Unit tests for top-level CLI app helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from ratchetr.cli import app
from ratchetr.cli.helpers.context import CLIContext
from ratchetr.cli.helpers.options import ReadinessOptions
from ratchetr.config import Config
from ratchetr.core.model_types import ReadinessLevel, ReadinessStatus, SeverityLevel
from ratchetr.paths import EnvOverrides, OutputFormat, OutputTarget, ResolvedPaths

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def _make_context(base: Path) -> CLIContext:
    tool_home = base / ".ratchetr"
    resolved = ResolvedPaths(
        repo_root=base,
        tool_home=tool_home,
        cache_dir=tool_home / ".cache",
        log_dir=tool_home / "logs",
        manifest_path=tool_home / "manifest.json",
        dashboard_path=tool_home / "dashboard.html",
        config_path=None,
    )
    return CLIContext(
        config=Config(),
        config_path=None,
        resolved_paths=resolved,
        env_overrides=EnvOverrides.from_environ(),
    )


def test_main_requires_command() -> None:
    with pytest.raises(SystemExit):
        _ = app.main([])


def test_main_unknown_command() -> None:
    with pytest.raises(SystemExit):
        _ = app.main(["unknown"])


def test_dashboard_format_for_output_rejects_unknown() -> None:
    class _UnknownFormat:
        value = "unknown"

    bogus_format = cast("OutputFormat", _UnknownFormat())

    with pytest.raises(SystemExit, match="Unsupported dashboard output format"):
        _ = app._dashboard_format_for_output(bogus_format)


def test_main_fails_when_handler_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app, "_command_handlers", dict)
    with pytest.raises(SystemExit):
        _ = app.main(["readiness"])


def test_resolve_dashboard_target_path_defaults(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    json_target = OutputTarget(OutputFormat.JSON, path=None)
    md_target = OutputTarget(OutputFormat.MARKDOWN, path=None)
    html_target = OutputTarget(OutputFormat.HTML, path=None)

    assert (
        app._resolve_dashboard_target_path(json_target, context) == context.resolved_paths.tool_home / "dashboard.json"
    )
    assert app._resolve_dashboard_target_path(md_target, context) == context.resolved_paths.tool_home / "dashboard.md"
    assert app._resolve_dashboard_target_path(html_target, context) == context.resolved_paths.dashboard_path


def test_execute_readiness_streams_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    args = SimpleNamespace(readiness=["status=blocked"], out="json", manifest=None)
    manifest_path = context.resolved_paths.manifest_path
    readiness = ReadinessOptions(
        enabled=True,
        level=ReadinessLevel.FILE,
        statuses=(ReadinessStatus.BLOCKED,),
        limit=3,
        severities=(SeverityLevel.WARNING,),
        include_details=False,
    )
    summary_data = {"summary": "data"}
    query_calls: dict[str, object] = {}
    output_lines: list[str] = []

    monkeypatch.setattr(app, "discover_manifest_or_exit", lambda *_args, **_kwargs: manifest_path)
    monkeypatch.setattr(app, "load_summary_from_manifest", lambda *_args, **_kwargs: summary_data)
    monkeypatch.setattr(app, "parse_readiness_tokens", lambda *_args, **_kwargs: readiness)

    def fake_query_readiness(summary_map: object, **kwargs: object) -> dict[str, str]:
        query_calls["template"] = summary_map
        query_calls.update(kwargs)
        return {"payload": "value"}

    def fake_render_data(payload: object, data_format: object) -> list[str]:
        assert isinstance(payload, dict)
        assert data_format is app.DataFormat.JSON
        return ["serialized"]

    def fake_echo(line: str) -> None:
        output_lines.append(line)

    monkeypatch.setattr(app, "query_readiness", fake_query_readiness)
    monkeypatch.setattr(app, "render_data", fake_render_data)
    monkeypatch.setattr(app, "_echo", fake_echo)

    exit_code = app._execute_readiness(args, context)

    assert exit_code == 0
    assert output_lines == ["serialized"]
    assert query_calls["template"] == summary_data
    assert query_calls["statuses"] == [ReadinessStatus.BLOCKED]
    assert query_calls["severities"] == [SeverityLevel.WARNING]
