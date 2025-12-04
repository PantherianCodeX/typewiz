# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Tests for the ratchet helpers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, TypedDict, cast

import pytest

from typewiz.core.model_types import SeverityLevel, SignaturePolicy
from typewiz.core.type_aliases import RelPath, RunId
from typewiz.manifest.typed import (
    EngineOptionsEntry,
    FileEntry,
    ManifestData,
    RunPayload,
    RunSummary,
)
from typewiz.ratchet import (
    apply_auto_update,
    build_ratchet_from_manifest,
    compare_manifest_to_ratchet,
    refresh_signatures,
)
from typewiz.ratchet.models import RatchetModel
from typewiz.ratchet.policies import compare_signatures

pytestmark = [pytest.mark.unit, pytest.mark.ratchet]

EXPECTED_ERROR_AFTER_UPDATE = 2
EXPECTED_ALLOWED_BASELINE = 1


class _DiagnosticDict(TypedDict, total=False):
    line: int
    column: int
    severity: str
    code: str | None
    message: str


def _make_manifest(
    per_file: dict[str, Counter[str]],
    *,
    plugin_args: list[str] | None = None,
) -> ManifestData:
    """Build a synthetic manifest with per-file diagnostics.

    Returns:
        dict: Manifest-like payload matching the provided diagnostics.

    """
    per_file_entries: list[FileEntry] = []
    for path, counts in per_file.items():
        diag_list: list[_DiagnosticDict] = []
        for severity, count in counts.items():
            diag_list.extend(
                {
                    "line": 1,
                    "column": 1,
                    "severity": severity,
                    "code": f"{severity[:1].upper()}{index}",
                    "message": f"{severity} {index}",
                }
                for index in range(count)
            )
        per_file_entries.append(
            cast(
                FileEntry,
                {
                    "path": path,
                    "errors": counts.get("error", 0),
                    "warnings": counts.get("warning", 0),
                    "information": counts.get("information", 0),
                    "diagnostics": diag_list,
                },
            )
        )
    engine_options: EngineOptionsEntry = {
        "profile": "baseline",
        "pluginArgs": plugin_args or ["--strict"],
        "include": [RelPath("src")],
        "exclude": [],
    }
    summary_totals = cast(
        RunSummary,
        {
            "errors": sum(counts.get("error", 0) for counts in per_file.values()),
            "warnings": sum(counts.get("warning", 0) for counts in per_file.values()),
            "information": sum(counts.get("information", 0) for counts in per_file.values()),
            "total": sum(counts.total() for counts in per_file.values()),
            "severityBreakdown": {},
            "ruleCounts": {},
            "categoryCounts": {},
        },
    )
    run_payload = cast(
        RunPayload,
        {
            "tool": "pyright",
            "mode": "current",
            "command": ["pyright", "--strict"],
            "exitCode": 0,
            "durationMs": 1.0,
            "summary": summary_totals,
            "perFile": per_file_entries,
            "perFolder": [],
            "engineOptions": engine_options,
        },
    )
    manifest = cast(
        ManifestData,
        {
            "generatedAt": "2025-01-01T00:00:00Z",
            "projectRoot": "/project",
            "runs": [run_payload],
        },
    )
    return manifest


def test_build_ratchet_uses_manifest_counts() -> None:
    """Baseline budgets match the manifest counts for each severity."""
    per_file_counts = {"src/foo.py": Counter({"error": 1, "warning": 2})}
    manifest = _make_manifest(per_file_counts)
    ratchet = build_ratchet_from_manifest(
        manifest=manifest,
        runs=None,
        severities=[SeverityLevel.ERROR, SeverityLevel.WARNING],
        targets=None,
        manifest_path="baseline.json",
    )
    run_budget = ratchet.runs[RunId("pyright:current")]
    foo_budget = run_budget.paths["src/foo.py"]
    expected_counts = per_file_counts["src/foo.py"]
    assert foo_budget.severities[SeverityLevel.ERROR] == expected_counts["error"]
    assert foo_budget.severities[SeverityLevel.WARNING] == expected_counts["warning"]
    engine_signature = run_budget.engine_signature
    assert engine_signature is not None
    hash_value = engine_signature.get("hash")
    assert hash_value


def test_compare_detects_regressions_and_signature_changes() -> None:
    """Regression and signature mismatches are surfaced in the report."""
    baseline_manifest = _make_manifest({"src/foo.py": Counter({"error": 1})})
    ratchet = build_ratchet_from_manifest(
        manifest=baseline_manifest,
        runs=None,
        severities=[SeverityLevel.ERROR],
        targets=None,
        manifest_path="baseline.json",
    )
    regress_manifest = _make_manifest(
        {"src/foo.py": Counter({"error": 2})}, plugin_args=["--strict", "--verifytypes"]
    )
    report = compare_manifest_to_ratchet(manifest=regress_manifest, ratchet=ratchet, runs=None)
    assert report.has_violations()
    run_report = report.runs[0]
    assert run_report.violations[0].path == "src/foo.py"
    assert not run_report.signature_matches


def test_auto_update_reduces_budgets_but_respects_targets() -> None:
    """Auto-update ratchets only decrease budgets down to configured targets."""
    manifest = _make_manifest({"src/foo.py": Counter({"error": 3})})
    ratchet = build_ratchet_from_manifest(
        manifest=manifest,
        runs=None,
        severities=[SeverityLevel.ERROR],
        targets={"error": 1},
        manifest_path="baseline.json",
    )
    improved_manifest = _make_manifest({"src/foo.py": Counter({"error": 2})})
    updated = apply_auto_update(
        manifest=improved_manifest,
        ratchet=ratchet,
        runs=None,
        generated_at=improved_manifest.get("generatedAt") or "2025-01-01T00:00:00Z",
    )
    updated_budget = updated.runs[RunId("pyright:current")].paths["src/foo.py"]
    # decreased from 3 to 2 but not below target 1
    assert updated_budget.severities[SeverityLevel.ERROR] == EXPECTED_ERROR_AFTER_UPDATE


def test_report_payload_and_formatting() -> None:
    """Ratchet reports expose payloads and human-friendly lines."""
    baseline = _make_manifest({"src/foo.py": Counter({"error": 1})})
    ratchet = build_ratchet_from_manifest(
        manifest=baseline,
        runs=None,
        severities=[SeverityLevel.ERROR],
        targets=None,
        manifest_path="baseline.json",
    )
    regression = _make_manifest({"src/foo.py": Counter({"error": 2})})
    report = compare_manifest_to_ratchet(manifest=regression, ratchet=ratchet, runs=None)

    payload = report.to_payload()
    assert payload["has_violations"] is True
    runs_payload = cast(list[dict[str, Any]], payload["runs"])
    run_payload = runs_payload[0]
    violations = cast(list[dict[str, Any]], run_payload["violations"])
    assert violations[0]["actual"] == EXPECTED_ERROR_AFTER_UPDATE
    assert violations[0]["allowed"] == EXPECTED_ALLOWED_BASELINE

    lines = report.format_lines(ignore_signature=True)
    assert any("Violations" in line for line in lines)
    assert report.exit_code(ignore_signature=True) == 1


def test_compare_manifest_run_filter() -> None:
    manifest = _make_manifest({"src/foo.py": Counter({"error": 1})})
    ratchet = build_ratchet_from_manifest(
        manifest=manifest,
        runs=None,
        severities=[SeverityLevel.ERROR],
        targets=None,
        manifest_path="baseline.json",
    )
    report = compare_manifest_to_ratchet(
        manifest=manifest,
        ratchet=ratchet,
        runs=["pyright:current"],
    )
    assert len(report.runs) == 1


def test_refresh_signatures_updates_hash() -> None:
    manifest = _make_manifest({"src/foo.py": Counter({"error": 1})})
    ratchet = build_ratchet_from_manifest(
        manifest=manifest,
        runs=None,
        severities=[SeverityLevel.ERROR],
        targets=None,
        manifest_path="baseline.json",
    )
    altered_manifest = _make_manifest(
        {"src/foo.py": Counter({"error": 1})},
        plugin_args=["--strict", "--experimental"],
    )
    refreshed = refresh_signatures(
        manifest=altered_manifest,
        ratchet=ratchet,
        runs=None,
        generated_at="2025-01-02T00:00:00Z",
    )
    run_key = RunId("pyright:current")
    original_signature = ratchet.runs[run_key].engine_signature
    refreshed_signature = refreshed.runs[run_key].engine_signature
    assert original_signature is not None
    assert refreshed_signature is not None
    original_hash = original_signature.get("hash")
    new_hash = refreshed_signature.get("hash")
    assert original_hash and new_hash and original_hash != new_hash


def test_compare_signatures_respects_policy() -> None:
    matching = compare_signatures({"hash": "abc"}, {"hash": "abc"}, SignaturePolicy.FAIL)
    assert matching.matches
    assert not matching.should_fail()
    warn_check = compare_signatures({"hash": "abc"}, {"hash": "def"}, SignaturePolicy.WARN)
    assert not warn_check.matches
    assert warn_check.should_warn()
    fail_check = compare_signatures({"hash": "abc"}, {"hash": "xyz"}, SignaturePolicy.FAIL)
    assert fail_check.should_fail()


def test_compare_manifest_to_ratchet_skips_missing_runs() -> None:
    ratchet_model = RatchetModel.model_validate({
        "generatedAt": "2025-01-01T00:00:00Z",
        "manifestPath": None,
        "projectRoot": None,
        "runs": {
            "pyright:current": {
                "severities": [SeverityLevel.ERROR.value],
                "paths": {},
            }
        },
    })
    manifest = cast(ManifestData, {"runs": []})
    report = compare_manifest_to_ratchet(manifest=manifest, ratchet=ratchet_model, runs=None)
    assert report.runs == []


def test_apply_auto_update_skips_missing_manifest_runs() -> None:
    ratchet_model = RatchetModel.model_validate({
        "generatedAt": "2025-01-01T00:00:00Z",
        "manifestPath": None,
        "projectRoot": None,
        "runs": {
            "pyright:current": {
                "severities": [SeverityLevel.ERROR.value],
                "paths": {
                    "src/foo.py": {"severities": {SeverityLevel.ERROR.value: 1}},
                },
            }
        },
    })
    manifest = cast(ManifestData, {"runs": []})
    updated = apply_auto_update(
        manifest=manifest,
        ratchet=ratchet_model,
        runs=None,
        generated_at="2025-01-02T00:00:00Z",
    )
    assert updated.runs == ratchet_model.runs


def test_refresh_signatures_handles_subset_and_missing_manifest(tmp_path: Path) -> None:
    ratchet_model = RatchetModel.model_validate({
        "generatedAt": "2025-01-01T00:00:00Z",
        "manifestPath": str(tmp_path / "typing_audit.json"),
        "projectRoot": str(tmp_path),
        "runs": {
            "pyright:current": {
                "severities": [SeverityLevel.ERROR.value],
                "paths": {},
            },
            "mypy:current": {
                "severities": [SeverityLevel.ERROR.value],
                "paths": {},
            },
        },
    })
    refreshed = refresh_signatures(
        manifest=cast(ManifestData, {"runs": []}),
        ratchet=ratchet_model,
        runs=[RunId("pyright:current")],
        generated_at="2025-02-01T00:00:00Z",
    )
    assert refreshed.runs.keys() == ratchet_model.runs.keys()
