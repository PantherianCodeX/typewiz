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

"""Unit tests for CLI options and context helpers."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from ratchetr.cli.helpers import options as options_module
from ratchetr.cli.helpers.context import CLIContext, build_cli_context, discover_manifest_or_exit
from ratchetr.cli.helpers.options import (
    StdoutFormat,
    build_path_overrides,
    finalise_targets,
    parse_readiness_tokens,
    parse_save_flag,
)
from ratchetr.config import Config
from ratchetr.core.model_types import ReadinessStatus, SeverityLevel
from ratchetr.paths import (
    EnvOverrides,
    ManifestDiagnostics,
    ManifestDiscoveryError,
    ManifestDiscoveryResult,
    OutputFormat,
    OutputTarget,
    PathOverrides,
    ResolvedPaths,
)

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


def test_parse_save_flag_applies_defaults(tmp_path: Path) -> None:
    save_flag = parse_save_flag([["json:out.json", "html"]])
    defaults = (OutputTarget(OutputFormat.MARKDOWN, tmp_path / "default.md"),)

    targets = finalise_targets(save_flag, defaults)

    assert save_flag.provided is True
    assert len(targets) == 2
    assert targets[0].format is OutputFormat.JSON
    assert targets[0].path == Path("out.json")
    assert targets[1].format is OutputFormat.HTML


def test_parse_save_flag_uses_defaults_when_no_args(tmp_path: Path) -> None:
    save_flag = parse_save_flag([[]])
    default_target = OutputTarget(OutputFormat.JSON, tmp_path / "manifest.json")

    targets = finalise_targets(save_flag, (default_target,))

    assert targets == (default_target,)


def test_parse_save_flag_rejects_unknown_format() -> None:
    with pytest.raises(SystemExit, match="Unknown output format"):
        _ = parse_save_flag([["unknown"]])


def test_parse_save_flag_rejects_disallowed_format() -> None:
    with pytest.raises(SystemExit, match="Unsupported format"):
        _ = parse_save_flag([["markdown"]], allowed_formats={OutputFormat.JSON})


def test_parse_save_flag_rejects_empty_path_component() -> None:
    with pytest.raises(SystemExit, match="Output path cannot be empty"):
        _ = parse_save_flag([["json:"]])


def test_parse_save_flag_rejects_empty_token() -> None:
    with pytest.raises(SystemExit, match="Output format cannot be empty"):
        _ = parse_save_flag([["  "]])


def test_stdout_format_from_str_rejects_unknown() -> None:
    with pytest.raises(SystemExit, match="Unknown output format"):
        _ = StdoutFormat.from_str("xml")


def test_parse_readiness_tokens_extracts_values() -> None:
    options = parse_readiness_tokens(
        ["details", "level=file", "status=blocked", "severity=warning", "limit=5"],
        flag_present=True,
    )

    assert options.enabled is True
    assert options.level.value == "file"
    assert options.statuses == (ReadinessStatus.BLOCKED,)
    assert options.severities == (SeverityLevel.WARNING,)
    assert options.limit == 5
    assert options.include_details is True


def test_parse_readiness_tokens_rejects_unknown_token() -> None:
    with pytest.raises(SystemExit, match="Unsupported readiness token"):
        _ = parse_readiness_tokens(["invalid=token"], flag_present=True)


def test_parse_readiness_tokens_handles_empty_and_no_details() -> None:
    options = parse_readiness_tokens([" ", "details", "no-details"], flag_present=True)
    assert options.include_details is False


def test_parse_readiness_tokens_rejects_negative_limit() -> None:
    with pytest.raises(SystemExit, match="non-negative"):
        _ = parse_readiness_tokens(["limit=-1"], flag_present=True)


def test_parse_positive_int_rejects_non_integer() -> None:
    with pytest.raises(SystemExit, match="must be an integer"):
        _ = options_module._parse_positive_int("abc")


def test_split_readiness_token_requires_delimiter() -> None:
    with pytest.raises(SystemExit, match="Invalid readiness token"):
        _ = options_module._split_readiness_token("status")


def test_split_readiness_token_rejects_blank_sections() -> None:
    with pytest.raises(SystemExit, match="non-empty key and value"):
        _ = options_module._split_readiness_token("limit=")
    with pytest.raises(SystemExit, match="non-empty key and value"):
        _ = options_module._split_readiness_token("=10")


def test_append_unique_skips_duplicates() -> None:
    statuses = [ReadinessStatus.BLOCKED]

    options_module._append_unique(statuses, ReadinessStatus.BLOCKED)
    options_module._append_unique(statuses, ReadinessStatus.CLOSE)

    assert statuses == [ReadinessStatus.BLOCKED, ReadinessStatus.CLOSE]


def test_build_path_overrides_populates_fields(tmp_path: Path) -> None:
    args = argparse.Namespace(
        config=tmp_path / "ratchetr.toml",
        root=tmp_path,
        ratchetr_dir=tmp_path / ".ratchetr",
        manifest=tmp_path / "manifest.json",
        cache_dir=tmp_path / ".ratchetr" / ".cache",
        log_dir=tmp_path / ".ratchetr" / "logs",
    )

    overrides = build_path_overrides(args)

    assert isinstance(overrides, PathOverrides)
    assert overrides.repo_root == tmp_path
    assert overrides.tool_home == tmp_path / ".ratchetr"
    assert overrides.manifest_path == tmp_path / "manifest.json"


def test_discover_manifest_or_exit_returns_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    diagnostics = ManifestDiagnostics(
        repo_root=tmp_path,
        tool_home=tmp_path / ".ratchetr",
        config_path=None,
        cli_manifest=None,
        env_overrides={},
        attempted_paths=(),
        matched_paths=(),
        glob_matches=(),
        ambiguity=None,
    )
    result = ManifestDiscoveryResult(manifest_path=tmp_path / "manifest.json", diagnostics=diagnostics, error=None)
    monkeypatch.setattr("ratchetr.cli.helpers.context.discover_manifest", lambda *_args, **_kwargs: result)

    resolved = discover_manifest_or_exit(context, cli_manifest=None)

    assert resolved == tmp_path / "manifest.json"


def test_discover_manifest_or_exit_emits_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    context = _make_context(tmp_path)
    diagnostics = ManifestDiagnostics(
        repo_root=tmp_path,
        tool_home=tmp_path / ".ratchetr",
        config_path=None,
        cli_manifest=tmp_path / "override.json",
        env_overrides={"RATCHETR_MANIFEST": tmp_path / "override.json"},
        attempted_paths=(tmp_path / "missing.json",),
        matched_paths=(),
        glob_matches=(tmp_path / "glob.json",),
        ambiguity="conflict",
    )
    result = ManifestDiscoveryResult(
        manifest_path=None,
        diagnostics=diagnostics,
        error=ManifestDiscoveryError("not found"),
    )
    monkeypatch.setattr("ratchetr.cli.helpers.context.discover_manifest", lambda *_args, **_kwargs: result)

    with pytest.raises(SystemExit):
        _ = discover_manifest_or_exit(context, cli_manifest=None)
    output = capsys.readouterr().out
    assert "manifest discovery failed" in output
    assert "attempted paths" in output
    assert "env overrides" in output
    assert "cli manifest" in output
    assert "glob matches" in output


def test_build_cli_context_uses_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = Config()
    loaded = SimpleNamespace(config=cfg, path=tmp_path / "ratchetr.toml")
    resolved_paths = ResolvedPaths(
        repo_root=tmp_path,
        tool_home=tmp_path / ".ratchetr",
        cache_dir=tmp_path / ".ratchetr" / ".cache",
        log_dir=tmp_path / ".ratchetr" / "logs",
        manifest_path=tmp_path / "manifest.json",
        dashboard_path=tmp_path / "dashboard.html",
        config_path=loaded.path,
    )
    monkeypatch.setattr("ratchetr.cli.helpers.context.load_config_with_metadata", lambda *_args, **_kwargs: loaded)
    monkeypatch.setattr("ratchetr.cli.helpers.context.resolve_paths", lambda **_kwargs: resolved_paths)

    overrides = PathOverrides(
        repo_root=tmp_path,
        config_path=loaded.path,
        tool_home=None,
        manifest_path=None,
        cache_dir=None,
        log_dir=None,
    )
    ctx = build_cli_context(overrides)

    assert ctx.config is cfg
    assert ctx.config_path == loaded.path
    assert ctx.resolved_paths is resolved_paths
