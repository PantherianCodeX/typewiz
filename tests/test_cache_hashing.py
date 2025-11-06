from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from typewiz.cache import collect_file_hashes
from typewiz.model_types import FileHashPayload
from typewiz.type_aliases import PathKey
from typewiz.utils import consume


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    consume(path.write_text(content, encoding="utf-8"))


def test_collect_file_hashes_sorted_output(tmp_path: Path) -> None:
    _write(tmp_path / "b.py", "print('b')\n")
    _write(tmp_path / "a.py", "print('a')\n")

    hashes, truncated = collect_file_hashes(tmp_path, paths=["."])

    assert not truncated
    assert list(hashes.keys()) == [PathKey("a.py"), PathKey("b.py")]


def test_collect_file_hashes_respects_gitignore(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    project_root = repo_root / "project"
    _write(project_root / "keep.py", "print('keep')\n")
    _write(project_root / "drop.py", "print('drop')\n")

    def fake_repo_root(_: Path) -> Path:
        return repo_root

    def fake_git_list(root: Path) -> set[str]:
        return {"project/keep.py"} if root == repo_root else set()

    monkeypatch.setattr("typewiz.cache._git_repo_root", fake_repo_root)
    monkeypatch.setattr("typewiz.cache._git_list_files", fake_git_list)

    hashes, _ = collect_file_hashes(project_root, paths=["."], respect_gitignore=True)

    assert list(hashes.keys()) == [PathKey("keep.py")]


def test_collect_file_hashes_reuses_baseline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.py"
    _write(target, "print('hello')\n")
    # Build initial baseline
    baseline, _ = collect_file_hashes(tmp_path, paths=["sample.py"])

    fingerprint_called = {"value": False}

    def record_fingerprint(path: Path) -> FileHashPayload:
        fingerprint_called["value"] = True
        return {"hash": "stub", "mtime": 0, "size": 0}

    monkeypatch.setattr("typewiz.cache._fingerprint", record_fingerprint)

    hashes, truncated = collect_file_hashes(
        tmp_path,
        paths=["sample.py"],
        baseline=baseline,
    )

    assert not truncated
    assert hashes == baseline
    assert not fingerprint_called["value"]


def test_collect_file_hashes_honours_worker_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write(tmp_path / "worker.py", "print('hi')\n")
    recorded: dict[str, Any] = {}

    def fake_compute(
        pending: Sequence[tuple[PathKey, Path]],
        workers: int,
    ) -> dict[PathKey, FileHashPayload]:
        recorded["workers"] = workers
        return {key: {"hash": "stub", "mtime": 0, "size": 0} for key, _ in pending}

    monkeypatch.setenv("TYPEWIZ_HASH_WORKERS", "4")
    monkeypatch.setattr("typewiz.cache._compute_hashes", fake_compute)

    hashes, _ = collect_file_hashes(tmp_path, paths=["worker.py"])

    assert recorded["workers"] == 4
    assert list(hashes.keys()) == [PathKey("worker.py")]
