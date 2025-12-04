# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Callable
from io import TextIOBase
from pathlib import Path
from typing import Any, cast

import pytest

from typewiz._internal import cache as cache_module
from typewiz._internal.cache import EngineCache
from typewiz.core.model_types import FileHashPayload, Mode, SeverityLevel
from typewiz.core.type_aliases import PathKey, RelPath, ToolName
from typewiz.core.types import Diagnostic


def _make_diagnostic(path: Path) -> Diagnostic:
    return Diagnostic(
        tool=ToolName("pyright"),
        severity=SeverityLevel.ERROR,
        path=path,
        line=1,
        column=1,
        code="E001",
        message="boom",
        raw={},
    )


def _repo_root_resolver(repo_root: Path) -> Callable[[Path], Path]:
    def _inner(_: Path) -> Path:
        return repo_root

    return _inner


def _git_list_files_factory(entries: set[str]) -> Callable[[Path], set[str]]:
    def _inner(_: Path) -> set[str]:
        return entries

    return _inner


def test_resolve_hash_workers_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cache_module._HASH_WORKER_ENV, "auto")
    value = cache_module._resolve_hash_workers()
    assert value >= 1
    monkeypatch.setenv(cache_module._HASH_WORKER_ENV, "4")
    assert cache_module._resolve_hash_workers() == 4
    monkeypatch.setenv(cache_module._HASH_WORKER_ENV, "not-a-number")
    assert cache_module._resolve_hash_workers() == 0
    monkeypatch.setenv(cache_module._HASH_WORKER_ENV, "  ")
    assert cache_module._resolve_hash_workers() == 0


def test_effective_hash_workers_with_invalid_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cache_module._HASH_WORKER_ENV, "2")
    assert cache_module._effective_hash_workers(3) == 3
    assert cache_module._effective_hash_workers("auto") >= 1
    assert cache_module._effective_hash_workers("bogus") == 2


def test_normalise_helpers() -> None:
    mapping = cache_module._normalise_category_mapping({
        "unknownChecks": [" Foo ", "foo", "BAR "],
        "bad": ["ignored"],
    })
    assert mapping["unknownChecks"] == ["Foo", "BAR"]
    override = cache_module._normalise_override_entry({
        "path": " src ",
        "profile": " strict ",
        "pluginArgs": ["--first", "--first"],
        "include": ["apps", " "],
        "exclude": ["tmp", ""],
    })
    assert override["path"] == "src"
    assert override["profile"] == "strict"
    assert override["pluginArgs"] == ["--first", "--first"]
    assert override["include"] == [RelPath("apps")]
    assert override["exclude"] == [RelPath("tmp")]
    diag = cache_module._normalise_diagnostic_payload({"tool": "pyright", "path": "pkg/app.py"})
    assert diag["tool"] == "pyright"
    file_hash = cache_module._normalise_file_hash_payload({"hash": "abc", "size": "10"})
    assert file_hash["size"] == 10


def test_engine_cache_round_trip(tmp_path: Path) -> None:
    cache = EngineCache(tmp_path)
    key = cache.key_for("pyright", Mode.CURRENT, [RelPath("src/app.py")], ["--strict"])
    file_hashes: dict[PathKey, FileHashPayload] = {
        PathKey("src/app.py"): {
            "hash": "abc",
            "mtime": 1,
            "size": 10,
        },
    }
    diagnostics = [_make_diagnostic(Path("src/app.py"))]
    cache.update(
        key,
        file_hashes,
        command=["pyright"],
        exit_code=0,
        duration_ms=1.23,
        diagnostics=diagnostics,
        profile="strict",
        config_file=tmp_path / "pyrightconfig.json",
        plugin_args=["--strict"],
        include=[RelPath("src")],
        exclude=[],
        overrides=[],
        category_mapping={"unknownChecks": ["foo"]},
        tool_summary={"errors": 1, "warnings": 0, "information": 0, "total": 1},
    )
    peeked = cache.peek_file_hashes(key)
    assert peeked == file_hashes
    cache.save()

    reloaded = EngineCache(tmp_path)
    cached = reloaded.get(key, file_hashes)
    assert cached is not None
    assert cached.command == ["pyright"]
    assert cached.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    mismatch = reloaded.get(
        key,
        {PathKey("src/app.py"): cast(FileHashPayload, {"hash": "different"})},
    )
    assert mismatch is None


def test_collect_file_hashes_respects_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    file_a = src_dir / "app.py"
    file_b = src_dir / "util.py"
    _ = file_a.write_text("print('a')", encoding="utf-8")
    _ = file_b.write_text("print('b')", encoding="utf-8")

    stat_a = file_a.stat()
    baseline: dict[PathKey, FileHashPayload] = {
        PathKey("src/app.py"): {
            "hash": "abc",
            "mtime": int(stat_a.st_mtime_ns),
            "size": stat_a.st_size,
        },
    }

    hashes, truncated = cache_module.collect_file_hashes(
        tmp_path,
        ["src"],
        max_files=1,
        respect_gitignore=False,
        baseline=baseline,
        max_bytes=10_000,
        hash_workers=0,
    )
    assert truncated is True
    assert PathKey("src/app.py") in hashes

    # Force gitignore-aware scan with mocked git response.
    monkeypatch.setattr(cache_module, "_git_repo_root", _repo_root_resolver(tmp_path))
    monkeypatch.setattr(
        cache_module,
        "_git_list_files",
        _git_list_files_factory({"src/app.py"}),
    )
    filtered, truncated_flag = cache_module.collect_file_hashes(
        tmp_path,
        ["src"],
        respect_gitignore=True,
        max_files=None,
        baseline=None,
        max_bytes=None,
        hash_workers=0,
    )
    assert truncated_flag is False
    assert set(filtered) == {PathKey("src/app.py")}


def test_compute_hashes_with_workers(tmp_path: Path) -> None:
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    _ = file_a.write_text("print('a')", encoding="utf-8")
    _ = file_b.write_text("print('b')", encoding="utf-8")
    pending = [(PathKey("a.py"), file_a), (PathKey("b.py"), file_b)]
    hashes = cache_module._compute_hashes(pending, workers=2)
    assert set(hashes) == {PathKey("a.py"), PathKey("b.py")}


def test_fingerprint_path_handles_missing_and_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing.py"
    assert cache_module._fingerprint(missing) == {"missing": True}

    unreadable = tmp_path / "blocked.py"
    _ = unreadable.write_text("print('x')", encoding="utf-8")
    original_open = Path.open

    def fake_open(self: Path, *args: Any, **kwargs: Any) -> TextIOBase:
        if self == unreadable:
            raise OSError("denied")
        return cast(TextIOBase, original_open(self, *args, **kwargs))

    monkeypatch.setattr(Path, "open", fake_open)
    assert cache_module._fingerprint(unreadable) == {"unreadable": True}


def test_relative_key_handles_external_paths(tmp_path: Path) -> None:
    outside = tmp_path.parent / "external.py"
    _ = outside.write_text("print('x')", encoding="utf-8")
    key_inside = cache_module._relative_key(tmp_path, tmp_path / "pkg/app.py")
    key_outside = cache_module._relative_key(tmp_path, outside)
    assert str(key_inside) == "pkg/app.py"
    assert key_outside.startswith("/")
