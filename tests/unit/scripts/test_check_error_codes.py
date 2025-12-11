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

"""Tests for the check_error_codes maintenance script."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts import check_error_codes

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

pytestmark = pytest.mark.unit


def test_discover_duplicates_identifies_only_repeated_codes() -> None:
    codes: list[str] = ["TW001", "TW002", "TW001", "TW003", "TW002"]
    duplicates = check_error_codes._discover_duplicates(codes)
    assert duplicates == {"TW001", "TW002"}


def test_main_succeeds_when_registry_and_docs_match(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def _fake_loader(_: Path) -> Iterable[str]:
        return ["TW001", "TW002"]

    monkeypatch.setattr(check_error_codes, "_load_error_codes", _fake_loader)
    monkeypatch.setattr(
        check_error_codes,
        "_load_documented_codes",
        lambda _doc_path: {"TW001", "TW002"},
    )

    exit_code = check_error_codes.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "[ratchetr] error code registry and documentation are in sync" in captured.out
    assert not captured.err


def test_main_reports_missing_documentation(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def _fake_loader(_: Path) -> Iterable[str]:
        return ["TW001"]

    monkeypatch.setattr(check_error_codes, "_load_error_codes", _fake_loader)
    monkeypatch.setattr(
        check_error_codes,
        "_load_documented_codes",
        lambda doc_path: (_ for _ in ()).throw(FileNotFoundError(f"documentation missing: {doc_path}")),
    )

    exit_code = check_error_codes.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "[ratchetr] documentation missing:" in captured.err


def test_main_reports_missing_and_orphaned_codes(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def _fake_loader(_: Path) -> Iterable[str]:
        # Registry contains TW001 and TW002
        return ["TW001", "TW002"]

    monkeypatch.setattr(check_error_codes, "_load_error_codes", _fake_loader)
    monkeypatch.setattr(
        check_error_codes,
        "_load_documented_codes",
        lambda _doc_path: {"TW001", "TW003"},
    )

    exit_code = check_error_codes.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "missing codes in docs: TW002" in captured.err
    assert "unknown codes in docs: TW003" in captured.err


def test_main_reports_duplicate_codes_in_registry(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def _fake_loader(_: Path) -> Iterable[str]:
        # Registry contains a duplicate TW001
        return ["TW001", "TW001"]

    monkeypatch.setattr(check_error_codes, "_load_error_codes", _fake_loader)
    monkeypatch.setattr(
        check_error_codes,
        "_load_documented_codes",
        lambda _doc_path: {"TW001"},
    )

    exit_code = check_error_codes.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "duplicate codes in registry: TW001" in captured.err


def test_main_propagates_runtime_error_from_loader(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def _loader(_: Path) -> Iterable[str]:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(check_error_codes, "_load_error_codes", _loader)

    exit_code = check_error_codes.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "[ratchetr] boom" in captured.err
