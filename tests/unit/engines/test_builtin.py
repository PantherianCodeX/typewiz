# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from typewiz.config import AuditConfig
from typewiz.core.model_types import CategoryMapping, Mode
from typewiz.core.type_aliases import ProfileName, RelPath, ToolName
from typewiz.engines.base import EngineContext, EngineOptions, EngineResult
from typewiz.engines.builtin.mypy import MypyEngine
from typewiz.engines.builtin.pyright import PyrightEngine

pytestmark = [pytest.mark.unit, pytest.mark.engine]


def _make_context(
    project_root: Path,
    *,
    mode: Mode = Mode.CURRENT,
    plugin_args: Sequence[str] | None = None,
    config_file: Path | None = None,
) -> EngineContext:
    options = EngineOptions(
        plugin_args=list(plugin_args or []),
        config_file=config_file,
        include=[RelPath("src")],
        exclude=[RelPath("tests")],
        profile=ProfileName("strict"),
    )
    return EngineContext(
        project_root=project_root,
        audit_config=AuditConfig(),
        mode=mode,
        engine_options=options,
    )


def test_mypy_engine_builds_command_with_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = MypyEngine()
    _ = (tmp_path / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")
    monkeypatch.setattr("typewiz.engines.builtin.mypy.python_executable", lambda: "py")
    context = _make_context(tmp_path, plugin_args=["--strict"])

    recorded: dict[str, list[str]] = {}

    def fake_run_mypy(root: Path, *, mode: Mode, command: list[str]) -> EngineResult:
        recorded["command"] = list(command)
        return EngineResult(
            engine=ToolName("pyright"),
            mode=mode,
            command=list(command),
            exit_code=0,
            duration_ms=1.0,
            diagnostics=[],
        )

    monkeypatch.setattr("typewiz.engines.builtin.mypy.run_mypy", fake_run_mypy)
    _ = engine.run(context, [])
    assert "--config-file" in recorded["command"]
    assert "--no-pretty" in recorded["command"]


def test_mypy_engine_full_mode_appends_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = MypyEngine()
    monkeypatch.setattr("typewiz.engines.builtin.mypy.python_executable", lambda: "py")
    context = _make_context(tmp_path, mode=Mode.FULL)
    paths = [RelPath("pkg/app.py"), RelPath("pkg/utils.py")]

    recorded: dict[str, list[str]] = {}

    def fake_run_mypy(root: Path, *, mode: Mode, command: list[str]) -> EngineResult:
        recorded["command"] = list(command)
        return EngineResult(
            engine=ToolName("pyright"),
            mode=mode,
            command=list(command),
            exit_code=0,
            duration_ms=1.0,
            diagnostics=[],
        )

    monkeypatch.setattr("typewiz.engines.builtin.mypy.run_mypy", fake_run_mypy)
    _ = engine.run(context, paths)
    assert recorded["command"][-2:] == ["pkg/app.py", "pkg/utils.py"]
    assert "--hide-error-context" in recorded["command"]


def test_mypy_engine_run_invokes_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = MypyEngine()
    context = _make_context(tmp_path)
    captured: dict[str, object] = {}

    def fake_run_mypy(root: Path, *, mode: Mode, command: list[str]) -> object:
        captured["root"] = root
        captured["mode"] = mode
        captured["command"] = command
        return "result"

    monkeypatch.setattr("typewiz.engines.builtin.mypy.run_mypy", fake_run_mypy)
    _ = engine.run(context, [])
    assert captured["root"] == tmp_path
    assert captured["mode"] == Mode.CURRENT


def test_pyright_engine_current_prefers_default_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = PyrightEngine()
    default_config = tmp_path / "pyrightconfig.json"
    _ = default_config.write_text("{}", encoding="utf-8")
    context = _make_context(tmp_path)

    recorded: dict[str, list[str]] = {}

    def fake_run_pyright(root: Path, *, mode: Mode, command: list[str]) -> EngineResult:
        recorded["command"] = list(command)
        return EngineResult(
            engine=ToolName("pyright"),
            mode=mode,
            command=list(command),
            exit_code=0,
            duration_ms=1.0,
            diagnostics=[],
        )

    monkeypatch.setattr("typewiz.engines.builtin.pyright.run_pyright", fake_run_pyright)
    _ = engine.run(context, [])
    assert "--project" in recorded["command"]
    assert str(default_config) in recorded["command"]


def test_pyright_engine_full_with_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = PyrightEngine()
    context = _make_context(tmp_path, mode=Mode.FULL, plugin_args=["--verifytypes"])
    paths = [RelPath("src/app.py")]
    context_no_paths = _make_context(tmp_path, mode=Mode.FULL)

    recorded: dict[str, list[str]] = {}

    def fake_run_pyright(root: Path, *, mode: Mode, command: list[str]) -> EngineResult:
        recorded["command"] = list(command)
        return EngineResult(
            engine=ToolName("pyright"),
            mode=mode,
            command=list(command),
            exit_code=0,
            duration_ms=1.0,
            diagnostics=[],
        )

    monkeypatch.setattr("typewiz.engines.builtin.pyright.run_pyright", fake_run_pyright)
    _ = engine.run(context, paths)
    assert recorded["command"][-1] == "src/app.py"
    assert "--verifytypes" in recorded["command"]
    _ = engine.run(context_no_paths, [])
    assert str(tmp_path) in recorded["command"]


def test_pyright_fingerprint_targets_prefers_explicit(tmp_path: Path) -> None:
    engine = PyrightEngine()
    explicit = tmp_path / "custom.json"
    _ = explicit.write_text("{}", encoding="utf-8")
    context = _make_context(tmp_path, config_file=explicit)
    targets = engine.fingerprint_targets(context, [])
    assert targets == [str(explicit)]


def test_mypy_fingerprint_targets_includes_config(tmp_path: Path) -> None:
    engine = MypyEngine()
    config_path = tmp_path / "mypy.ini"
    _ = config_path.write_text("[mypy]\n", encoding="utf-8")
    context = _make_context(tmp_path, config_file=config_path)
    targets = engine.fingerprint_targets(context, [])
    assert targets == [str(config_path)]


def test_pyright_fingerprint_targets_prefers_default(tmp_path: Path) -> None:
    engine = PyrightEngine()
    default = tmp_path / "pyrightconfig.json"
    _ = default.write_text("{}", encoding="utf-8")
    context = _make_context(tmp_path)
    assert engine.fingerprint_targets(context, []) == [str(default)]


def test_pyright_fingerprint_targets_empty_when_missing(tmp_path: Path) -> None:
    engine = PyrightEngine()
    context = _make_context(tmp_path)
    assert engine.fingerprint_targets(context, []) == []


def test_pyright_engine_current_without_config_uses_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = PyrightEngine()
    context = _make_context(tmp_path)

    recorded: dict[str, list[str]] = {}

    def fake_run_pyright(root: Path, *, mode: Mode, command: list[str]) -> EngineResult:
        recorded["command"] = list(command)
        return EngineResult(
            engine=ToolName("pyright"),
            mode=mode,
            command=list(command),
            exit_code=0,
            duration_ms=1.0,
            diagnostics=[],
        )

    monkeypatch.setattr("typewiz.engines.builtin.pyright.run_pyright", fake_run_pyright)
    _ = engine.run(context, [])
    assert str(tmp_path) in recorded["command"]


def test_category_mapping_contains_expected_keys() -> None:
    mapping: CategoryMapping = PyrightEngine().category_mapping()
    assert "unknownChecks" in mapping
    assert MypyEngine().category_mapping()["unknownChecks"]
