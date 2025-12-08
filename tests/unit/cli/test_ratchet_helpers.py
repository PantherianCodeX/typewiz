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

"""Unit tests for CLI Ratchet Helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from ratchetr.cli.helpers.ratchet import (
    DEFAULT_RATCHET_FILENAME,
    DEFAULT_SEVERITIES,
    discover_manifest_path,
    discover_ratchet_path,
    ensure_parent,
    normalise_runs,
    parse_target_entries,
    resolve_limit,
    resolve_path,
    resolve_runs,
    resolve_severities,
    resolve_signature_policy,
    resolve_summary_only,
    split_target_mapping,
)
from ratchetr.core.model_types import SeverityLevel, SignaturePolicy
from ratchetr.core.type_aliases import RunId

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.ratchet]


def test_parse_target_entries_supports_global_and_scoped() -> None:
    entries = ["error=1", "pyright:current.warning=2"]
    result = parse_target_entries(entries)
    assert result == {"error": 1, "pyright:current.warning": 2}


def test_split_target_mapping_separates_scoped_targets() -> None:
    global_targets, per_run = split_target_mapping({"error": 1, "tool:mode.warning": 2})
    assert global_targets == {SeverityLevel.ERROR: 1}
    assert per_run == {"tool:mode": {SeverityLevel.WARNING: 2}}


def test_discover_manifest_path_prefers_explicit(tmp_path: Path) -> None:
    manifest = tmp_path / "custom.json"
    _ = manifest.write_text("{}", encoding="utf-8")
    discovered = discover_manifest_path(
        tmp_path,
        explicit=manifest,
        configured=None,
    )
    assert discovered == manifest.resolve()


def test_discover_manifest_path_falls_back_to_conventional(tmp_path: Path) -> None:
    manifest = tmp_path / "typing_audit.json"
    _ = manifest.write_text("{}", encoding="utf-8")
    discovered = discover_manifest_path(tmp_path, explicit=None, configured=None)
    assert discovered == manifest.resolve()


def test_discover_manifest_path_prefers_configured_when_present(tmp_path: Path) -> None:
    configured = tmp_path / "reports" / "typing_audit.json"
    configured.parent.mkdir(parents=True, exist_ok=True)
    _ = configured.write_text("{}", encoding="utf-8")
    manifest = discover_manifest_path(tmp_path, explicit=None, configured=configured)
    assert manifest == configured.resolve()


def test_discover_manifest_path_errors_when_missing(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match=r".*"):
        _ = discover_manifest_path(tmp_path, explicit=None, configured=None)


def test_discover_ratchet_path_defaults(tmp_path: Path) -> None:
    result = discover_ratchet_path(
        tmp_path,
        explicit=None,
        configured=None,
        require_exists=False,
    )
    assert result == (tmp_path / DEFAULT_RATCHET_FILENAME).resolve()


def test_discover_manifest_path_requires_existing(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match=r".*"):
        _ = discover_manifest_path(tmp_path, explicit=tmp_path / "missing.json", configured=None)


def test_discover_ratchet_path_prefers_configured(tmp_path: Path) -> None:
    configured = tmp_path / "configs" / "ratchet.json"
    configured.parent.mkdir(parents=True, exist_ok=True)
    _ = configured.write_text("{}", encoding="utf-8")
    resolved = discover_ratchet_path(
        tmp_path,
        explicit=None,
        configured=configured,
        require_exists=True,
    )
    assert resolved == configured.resolve()


def test_discover_ratchet_path_requires_existing(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match=r".*"):
        _ = discover_ratchet_path(
            tmp_path,
            explicit=tmp_path / "missing.json",
            configured=None,
            require_exists=True,
        )


def test_discover_ratchet_path_requires_existing_configured(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match=r".*"):
        _ = discover_ratchet_path(
            tmp_path,
            explicit=None,
            configured=tmp_path / "absent.json",
            require_exists=True,
        )


def test_resolve_runs_prefers_cli_values() -> None:
    assert resolve_runs(["pyright:current"], [RunId("mypy:current")]) == [RunId("pyright:current")]
    assert resolve_runs(None, [RunId("mypy:current")]) == [RunId("mypy:current")]
    assert resolve_runs([], []) is None
    assert normalise_runs(["", RunId("custom")]) == [RunId("custom")]


def test_resolve_severities_handles_defaults() -> None:
    severities = resolve_severities(None, [SeverityLevel.ERROR])
    assert severities == [SeverityLevel.ERROR]

    severities_override = resolve_severities("error,warning", [])
    assert severities_override == [SeverityLevel.ERROR, SeverityLevel.WARNING]
    deduped = resolve_severities("error,ERROR,warning", [])
    assert deduped == [SeverityLevel.ERROR, SeverityLevel.WARNING]


def test_resolve_severities_falls_back_to_defaults_when_empty() -> None:
    severities = resolve_severities(None, [])
    assert severities == list(DEFAULT_SEVERITIES)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("fail", SignaturePolicy.FAIL),
        ("WARN", SignaturePolicy.WARN),
        (None, SignaturePolicy.FAIL),
    ],
)
def test_resolve_signature_policy_accepts_permitted_values(value: str | None, expected: SignaturePolicy) -> None:
    assert resolve_signature_policy(value, SignaturePolicy.FAIL) is expected


def test_resolve_signature_policy_rejects_invalid() -> None:
    with pytest.raises(SystemExit, match=r".*"):
        _ = resolve_signature_policy("maybe", SignaturePolicy.FAIL)


def test_resolve_summary_only_and_limit() -> None:
    assert resolve_summary_only(cli_summary=True, config_summary=False) is True
    assert resolve_summary_only(cli_summary=False, config_summary=True) is True
    assert resolve_summary_only(cli_summary=False, config_summary=False) is False
    assert resolve_limit(5, None) == 5
    assert resolve_limit(None, 10) == 10


def test_resolve_path_and_ensure_parent(tmp_path: Path) -> None:
    rel = Path("manifests/report.json")
    resolved = resolve_path(tmp_path, rel)
    assert resolved.is_absolute()
    target = tmp_path / "nested" / "file.txt"
    ensure_parent(target)
    assert target.parent.exists()
