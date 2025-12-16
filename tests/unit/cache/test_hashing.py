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

"""Unit tests for Cache Hashing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from ratchetr._infra import cache as cache_module
from ratchetr._infra.cache import collect_file_hashes
from ratchetr._infra.utils import consume
from ratchetr.core.type_aliases import PathKey

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ratchetr.core.model_types import FileHashPayload

pytestmark = pytest.mark.unit


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

    monkeypatch.setattr("ratchetr._infra.cache._git_repo_root", fake_repo_root)
    monkeypatch.setattr("ratchetr._infra.cache._git_list_files", fake_git_list)

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
        assert path.name == "sample.py"
        return {"hash": "stub", "mtime": 0, "size": 0}

    monkeypatch.setattr("ratchetr._infra.cache._fingerprint", record_fingerprint)

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

    monkeypatch.setenv("RATCHETR_HASH_WORKERS", "4")
    monkeypatch.setattr("ratchetr._infra.cache._compute_hashes", fake_compute)

    hashes, _ = collect_file_hashes(tmp_path, paths=["worker.py"])

    assert recorded["workers"] == 4
    assert list(hashes.keys()) == [PathKey("worker.py")]


def test_collect_file_hashes_filters_gitignored_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    repo_root = tmp_path
    project_root.mkdir()
    _write(project_root / "keep.py", "print('keep')")
    _write(project_root / "skip.py", "print('skip')")

    def fake_repo_root(_: Path) -> Path:
        return repo_root

    def fake_git_list_files(_: Path) -> set[str]:
        return {"project/keep.py", "outside.py"}

    monkeypatch.setattr(cache_module, "_git_repo_root", fake_repo_root)
    monkeypatch.setattr(cache_module, "_git_list_files", fake_git_list_files)

    hashes, truncated = collect_file_hashes(
        project_root,
        paths=["."],
        respect_gitignore=True,
        hash_workers=0,
    )
    assert not truncated
    assert list(hashes.keys()) == [PathKey("keep.py")]


def test_collect_file_hashes_enforces_bytes_budget(tmp_path: Path) -> None:
    _write(tmp_path / "one.py", "print('1')")
    _write(tmp_path / "two.py", "print('2')")
    hashes, truncated = collect_file_hashes(
        tmp_path,
        paths=["one.py", "two.py"],
        max_bytes=5,
        hash_workers=0,
    )
    assert truncated is True
    assert hashes == {}


def test_collect_file_hashes_stops_after_max_files(tmp_path: Path) -> None:
    _write(tmp_path / "one.py", "print('1')")
    _write(tmp_path / "two.py", "print('2')")
    hashes, truncated = collect_file_hashes(
        tmp_path,
        paths=["."],
        max_files=1,
        hash_workers=0,
    )
    assert truncated is True
    assert len(hashes) == 1
