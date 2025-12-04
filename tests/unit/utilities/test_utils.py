# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Utilities Utils."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import cast

import pytest

from typewiz._internal.utils import (
    CommandOutput,
    as_int,
    as_list,
    as_mapping,
    as_str,
    consume,
    default_full_paths,
    detect_tool_versions,
    file_lock,
    normalise_enums_for_json,
    require_json,
    resolve_project_root,
    run_command,
)
from typewiz._internal.utils import locks as locks_mod
from typewiz._internal.utils import versions as versions_mod
from typewiz.core.model_types import ReadinessStatus, SeverityLevel

pytestmark = pytest.mark.unit


def test_resolve_project_root_prefers_local_markers(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "pkg"
    nested.mkdir(parents=True)
    consume((workspace / "typewiz.toml").write_text("config_version = 0\n", encoding="utf-8"))

    assert resolve_project_root(nested) == workspace


def test_resolve_project_root_accepts_explicit_path_without_markers(tmp_path: Path) -> None:
    workspace = tmp_path / "explicit"
    workspace.mkdir()

    assert resolve_project_root(workspace) == workspace


def test_resolve_project_root_defaults_to_cwd_when_no_markers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_project_root() == tmp_path.resolve()


def test_resolve_project_root_raises_for_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "absent"
    with pytest.raises(FileNotFoundError):
        _ = resolve_project_root(missing)


def test_default_full_paths_detects_python_directories(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests" / "nested"
    tests_dir.mkdir(parents=True)
    consume((tests_dir / "sample.py").write_text("print('ok')\n", encoding="utf-8"))

    paths = default_full_paths(tmp_path)
    assert "tests" in paths


def test_default_full_paths_falls_back_to_current_directory(tmp_path: Path) -> None:
    assert default_full_paths(tmp_path) == ["."]


def test_resolve_project_root_handles_file_inputs(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    consume((workspace / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8"))
    target = workspace / "pkg" / "module.py"
    target.parent.mkdir(parents=True)
    consume(target.write_text("print('file')\n", encoding="utf-8"))

    assert resolve_project_root(target) == workspace


def test_normalise_enums_for_json_converts_keys_and_nested_values() -> None:
    payload = {
        ReadinessStatus.READY: {
            "status": ReadinessStatus.CLOSE,
            "counts": (ReadinessStatus.BLOCKED,),
        },
        "nested": [{"severity": SeverityLevel.ERROR}],
    }
    normalised = normalise_enums_for_json(payload)
    assert isinstance(normalised, dict)
    normalised_dict = cast(dict[str, object], normalised)
    ready_raw = normalised_dict.get("ready")
    assert isinstance(ready_raw, dict)
    ready_bucket = cast(dict[str, object], ready_raw)
    assert ready_bucket.get("status") == "close"
    counts_value = ready_bucket.get("counts")
    assert isinstance(counts_value, list) and counts_value
    assert counts_value[0] == "blocked"
    nested_raw = normalised_dict.get("nested")
    assert isinstance(nested_raw, list) and nested_raw
    first_nested = cast(dict[str, object], nested_raw[0])
    assert first_nested.get("severity") == "error"


def test_require_json_uses_fallback_payload() -> None:
    data = require_json(" ", fallback='{"ok": 1}')
    assert data == {"ok": 1}


def test_json_cast_helpers_handle_defaults() -> None:
    assert as_mapping({"a": 1}) == {"a": 1}
    assert as_list([1, 2]) == [1, 2]
    assert as_str(3, default="x") == "x"
    assert as_int("42") == 42
    assert as_int("oops", default=5) == 5


def test_file_lock_supports_fallback_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lock_path = tmp_path / "lock"
    with file_lock(lock_path):
        consume(lock_path.write_text("locked\n", encoding="utf-8"))

    monkeypatch.setattr(locks_mod, "fcntl_module", None)
    monkeypatch.setattr(locks_mod, "msvcrt_module", None)
    with file_lock(lock_path):
        consume(lock_path.write_text("fallback\n", encoding="utf-8"))


def test_file_lock_prefers_fcntl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyFcntl:
        LOCK_EX = 1
        LOCK_UN = 2

        def __init__(self) -> None:
            super().__init__()
            self.calls: list[int] = []

        def flock(self, _fd: int, operation: int) -> None:
            self.calls.append(operation)

    dummy = DummyFcntl()
    monkeypatch.setattr(locks_mod, "fcntl_module", dummy)
    monkeypatch.setattr(locks_mod, "msvcrt_module", None)
    with file_lock(tmp_path / "fcntl.lock"):
        pass
    assert dummy.calls == [dummy.LOCK_EX, dummy.LOCK_UN]


def test_file_lock_handles_msvcrt_branch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyMsvcrt:
        LK_LOCK = 1
        LK_UNLCK = 2

        def __init__(self) -> None:
            super().__init__()
            self.operations: list[int] = []

        def locking(self, _fd: int, mode: int, _size: int) -> None:
            self.operations.append(mode)

    dummy = DummyMsvcrt()
    monkeypatch.setattr(locks_mod, "fcntl_module", None)
    monkeypatch.setattr(locks_mod, "msvcrt_module", dummy)
    with file_lock(tmp_path / "msvcrt.lock"):
        pass
    assert dummy.operations == [dummy.LK_LOCK, dummy.LK_UNLCK]


def test_run_command_enforces_allowlist() -> None:
    result = run_command([sys.executable, "-c", "print('ok')"], allowed={sys.executable})
    assert "ok" in result.stdout
    with pytest.raises(ValueError):
        _ = run_command([sys.executable, "-c", "print('blocked')"], allowed={"python"})


def test_run_command_requires_arguments() -> None:
    with pytest.raises(ValueError):
        _ = run_command([])
    with pytest.raises(TypeError):
        _ = run_command([""])


def test_run_command_logs_warning_on_failure(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="typewiz.internal.process")
    result = run_command([sys.executable, "-c", "import sys; sys.exit(1)"])
    assert result.exit_code != 0
    assert any("Command failed" in record.message for record in caplog.records)


def test_detect_tool_versions_parses_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run_command(args: list[str], **_: object) -> CommandOutput:
        payload = "pyright 1.2.3" if args[0] == "pyright" else "mypy 1.5.0"
        return CommandOutput(args=args, stdout=payload, stderr="", exit_code=0, duration_ms=0.1)

    monkeypatch.setattr(versions_mod, "run_command", _fake_run_command)
    monkeypatch.setattr(versions_mod, "python_executable", lambda: sys.executable)

    versions = detect_tool_versions(["pyright", "mypy", "pyright"])
    assert versions == {"pyright": "1.2.3", "mypy": "1.5.0"}


def test_detect_tool_versions_swallows_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_run_command(*_: object, **__: object) -> CommandOutput:
        raise RuntimeError("boom")

    monkeypatch.setattr(versions_mod, "run_command", _fail_run_command)
    monkeypatch.setattr(versions_mod, "python_executable", lambda: sys.executable)

    versions = detect_tool_versions(["pyright"])
    assert versions == {}
