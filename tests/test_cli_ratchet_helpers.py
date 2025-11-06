from __future__ import annotations

from pathlib import Path

import pytest

from typewiz.cli.helpers.ratchet import (
    DEFAULT_RATCHET_FILENAME,
    discover_manifest_path,
    discover_ratchet_path,
    parse_target_entries,
    resolve_runs,
    resolve_severities,
    resolve_signature_policy,
    split_target_mapping,
)


def test_parse_target_entries_supports_global_and_scoped() -> None:
    entries = ["errors=1", "pyright:current.warning=2"]
    result = parse_target_entries(entries)
    assert result == {"errors": 1, "pyright:current.warning": 2}


def test_split_target_mapping_separates_scoped_targets() -> None:
    global_targets, per_run = split_target_mapping({"errors": 1, "tool:mode.warning": 2})
    assert global_targets == {"error": 1}
    assert per_run == {"tool:mode": {"warning": 2}}


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


def test_discover_ratchet_path_defaults(tmp_path: Path) -> None:
    result = discover_ratchet_path(
        tmp_path,
        explicit=None,
        configured=None,
        require_exists=False,
    )
    assert result == (tmp_path / DEFAULT_RATCHET_FILENAME).resolve()


def test_resolve_runs_prefers_cli_values() -> None:
    assert resolve_runs(["pyright:current"], ["mypy:current"]) == ["pyright:current"]
    assert resolve_runs(None, ["mypy:current"]) == ["mypy:current"]


def test_resolve_severities_handles_defaults() -> None:
    severities = resolve_severities(None, ["error"])
    assert severities == ["error"]

    severities_override = resolve_severities("errors,warnings", [])
    assert severities_override == ["error", "warning"]


@pytest.mark.parametrize("value, expected", [("fail", "fail"), ("WARN", "warn"), (None, "fail")])
def test_resolve_signature_policy_accepts_permitted_values(
    value: str | None, expected: str
) -> None:
    assert resolve_signature_policy(value, "fail") == expected


def test_resolve_signature_policy_rejects_invalid() -> None:
    with pytest.raises(SystemExit):
        _ = resolve_signature_policy("maybe", "fail")
