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

"""Unit tests for Ratchet Services."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from ratchetr.core.model_types import SeverityLevel, SignaturePolicy
from ratchetr.core.type_aliases import RunId
from ratchetr.ratchet.models import RatchetModel
from ratchetr.ratchet.summary import RatchetFinding, RatchetReport, RatchetRunReport
from ratchetr.services import ratchet as ratchet_service
from ratchetr.services.ratchet import (
    RatchetFileExistsError,
    RatchetPathRequiredError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from ratchetr.manifest.typed import ManifestData

pytestmark = [pytest.mark.unit, pytest.mark.ratchet]


def _manifest(tmp_path: Path) -> ManifestData:
    return cast(
        "ManifestData",
        {
            "generatedAt": "2024-01-01T00:00:00Z",
            "schemaVersion": 1,
            "projectRoot": str(tmp_path),
            "runs": [],
        },
    )


def _ratchet_model(tmp_path: Path) -> RatchetModel:
    return RatchetModel.model_validate(
        {
            "generatedAt": "2024-01-01T00:00:00Z",
            "manifestPath": str(tmp_path / "typing_audit.json"),
            "projectRoot": str(tmp_path),
            "runs": {
                "pyright:current": {
                    "severities": ["error"],
                    "paths": {},
                    "targets": {"error": 1},
                },
            },
        },
    )


def _detailed_manifest(
    *,
    per_file_counts: Mapping[str, int],
    plugin_args: Sequence[str] | None = None,
) -> ManifestData:
    per_file_entries: list[dict[str, object]] = []
    for path, count in per_file_counts.items():
        diagnostics = [
            {"line": 1, "column": 1, "severity": "error", "code": "E1", "message": "error"} for _ in range(count)
        ]
        per_file_entries.append({
            "path": path,
            "errors": count,
            "warnings": 0,
            "information": 0,
            "diagnostics": diagnostics,
        })
    summary: dict[str, object] = {
        "errors": sum(per_file_counts.values()),
        "warnings": 0,
        "information": 0,
        "total": sum(per_file_counts.values()),
        "severityBreakdown": {},
        "ruleCounts": {},
        "categoryCounts": {},
    }
    return cast(
        "ManifestData",
        {
            "generatedAt": "2025-01-01T00:00:00Z",
            "projectRoot": "/repo",
            "runs": [
                {
                    "tool": "pyright",
                    "mode": "current",
                    "command": ["pyright"],
                    "exitCode": 0,
                    "durationMs": 1.0,
                    "summary": summary,
                    "perFile": per_file_entries,
                    "perFolder": [],
                    "engineOptions": {
                        "profile": "baseline",
                        "pluginArgs": list(plugin_args or ["--strict"]),
                        "include": ["src"],
                        "exclude": [],
                    },
                }
            ],
        },
    )


def test_init_ratchet_invokes_builder_and_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(tmp_path)
    output_path = tmp_path / "ratchet.json"
    model = _ratchet_model(tmp_path)
    captured: dict[str, dict[str, object]] = {}

    def fake_build(**kwargs: object) -> RatchetModel:
        captured["build"] = dict(kwargs)
        return model

    writes: list[tuple[Path, RatchetModel]] = []

    def fake_write(path: Path, built: RatchetModel) -> None:
        writes.append((path, built))

    monkeypatch.setattr(ratchet_service, "_build_ratchet_from_manifest", fake_build)
    monkeypatch.setattr(ratchet_service, "_write_ratchet", fake_write)

    result = ratchet_service.init_ratchet(
        manifest=manifest,
        runs=None,
        manifest_path=tmp_path / "typing_audit.json",
        severities=None,
        targets=None,
        output_path=output_path,
        force=True,
    )

    assert result.output_path == output_path
    assert writes == [(output_path, model)]
    assert captured["build"]["manifest"] is manifest


def test_init_ratchet_requires_force(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    output_path = tmp_path / "ratchet.json"
    _ = output_path.write_text("{}", encoding="utf-8")

    with pytest.raises(RatchetFileExistsError, match="Refusing to overwrite existing ratchet"):
        _ = ratchet_service.init_ratchet(
            manifest=manifest,
            runs=None,
            manifest_path=tmp_path / "typing_audit.json",
            severities=None,
            targets=None,
            output_path=output_path,
            force=False,
        )


def test_check_ratchet_warns_on_signature_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ratchet_path = tmp_path / "ratchet.json"
    model = _ratchet_model(tmp_path)

    def fake_load(path: Path) -> RatchetModel | None:
        return model if path == ratchet_path else None

    monkeypatch.setattr(ratchet_service, "_load_ratchet", fake_load)

    run_report = RatchetRunReport(
        run_id=RunId("pyright:current"),
        severities=[SeverityLevel.ERROR],
        violations=[RatchetFinding(path="pkg", severity=SeverityLevel.ERROR, allowed=1, actual=2)],
        signature_matches=False,
    )
    report = RatchetReport(runs=[run_report])

    def fake_compare(**_: object) -> RatchetReport:
        return report

    monkeypatch.setattr(ratchet_service, "_compare_manifest_to_ratchet", fake_compare)

    result = ratchet_service.check_ratchet(
        manifest=_manifest(tmp_path),
        ratchet_path=ratchet_path,
        runs=None,
        signature_policy=SignaturePolicy.WARN,
    )

    assert result.warn_signature is True
    assert result.exit_code == 1
    assert result.ignore_signature is True


def test_update_ratchet_writes_updated_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ratchet_path = tmp_path / "ratchet.json"
    base_model = _ratchet_model(tmp_path)

    def fake_update_load(path: Path) -> RatchetModel | None:
        return base_model if path == ratchet_path else None

    monkeypatch.setattr(ratchet_service, "_load_ratchet", fake_update_load)

    report = RatchetReport(
        runs=[
            RatchetRunReport(
                run_id=RunId("pyright:current"),
                severities=[SeverityLevel.ERROR],
                violations=[],
            ),
        ],
    )

    def fake_update_compare(**_: object) -> RatchetReport:
        return report

    monkeypatch.setattr(ratchet_service, "_compare_manifest_to_ratchet", fake_update_compare)

    updated_model = _ratchet_model(tmp_path)

    def fake_update_auto(**_: object) -> RatchetModel:
        return updated_model

    monkeypatch.setattr(ratchet_service, "_apply_auto_update", fake_update_auto)

    writes: list[tuple[Path, RatchetModel]] = []

    def fake_update_write(path: Path, model: RatchetModel) -> None:
        writes.append((path, model))

    monkeypatch.setattr(ratchet_service, "_write_ratchet", fake_update_write)

    overrides: dict[str, int] | None = None
    applied_model: RatchetModel | None = None

    def fake_apply_overrides(model: RatchetModel, targets: dict[str, int]) -> None:
        nonlocal overrides, applied_model
        overrides = targets
        applied_model = model

    monkeypatch.setattr(ratchet_service, "apply_target_overrides", fake_apply_overrides)

    result = ratchet_service.update_ratchet(
        manifest=_manifest(tmp_path),
        ratchet_path=ratchet_path,
        runs=None,
        generated_at="2024-01-01T00:00:00Z",
        target_overrides={"error": 2},
        output_path=None,
        force=True,
        dry_run=False,
    )

    assert overrides == {"error": 2}
    assert applied_model is updated_model
    assert result.output_path == ratchet_path
    assert writes == [(ratchet_path, updated_model)]
    assert result.wrote_file is True


def test_update_ratchet_requires_existing_path(tmp_path: Path) -> None:
    with pytest.raises(RatchetPathRequiredError, match="Ratchet path is required"):
        _ = ratchet_service.update_ratchet(
            manifest=_manifest(tmp_path),
            ratchet_path=None,
            runs=None,
            generated_at="2024-01-01T00:00:00Z",
            target_overrides={},
            output_path=None,
            force=True,
            dry_run=False,
        )


def test_rebaseline_ratchet_writes_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ratchet_path = tmp_path / "ratchet.json"
    base_model = _ratchet_model(tmp_path)

    def fake_rebaseline_load(path: Path) -> RatchetModel | None:
        return base_model if path == ratchet_path else None

    monkeypatch.setattr(ratchet_service, "_load_ratchet", fake_rebaseline_load)
    refreshed_model = _ratchet_model(tmp_path)

    def fake_rebaseline_refresh(**_: object) -> RatchetModel:
        return refreshed_model

    monkeypatch.setattr(ratchet_service, "_refresh_signatures", fake_rebaseline_refresh)
    writes: list[tuple[Path, RatchetModel]] = []

    def fake_rebaseline_write(path: Path, model: RatchetModel) -> None:
        writes.append((path, model))

    monkeypatch.setattr(ratchet_service, "_write_ratchet", fake_rebaseline_write)

    output_path = tmp_path / "refreshed.json"
    result = ratchet_service.rebaseline_ratchet(
        manifest=_manifest(tmp_path),
        ratchet_path=ratchet_path,
        runs=None,
        generated_at="2024-02-01T00:00:00Z",
        output_path=output_path,
        force=True,
    )

    assert result.output_path == output_path
    assert writes == [(output_path, refreshed_model)]


def test_apply_target_overrides_merges_targets(tmp_path: Path) -> None:
    model = _ratchet_model(tmp_path)
    ratchet_service.apply_target_overrides(model, {"error": 5, "pyright:current.warning": 3})
    run_budget = model.runs[RunId("pyright:current")]
    assert run_budget.targets[SeverityLevel.ERROR] == 5
    assert run_budget.targets[SeverityLevel.WARNING] == 3


def test_init_rebaseline_check_and_update_flow(tmp_path: Path) -> None:
    manifest = _detailed_manifest(per_file_counts={"src/foo.py": 1})
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("", encoding="utf-8")
    baseline_path = tmp_path / "baseline.json"

    init_result = ratchet_service.init_ratchet(
        manifest=manifest,
        runs=None,
        manifest_path=manifest_path,
        severities=None,
        targets=None,
        output_path=baseline_path,
        force=True,
    )
    assert init_result.output_path == baseline_path

    mismatched_manifest = _detailed_manifest(
        per_file_counts={"src/foo.py": 2},
        plugin_args=["--strict", "--verifytypes"],
    )
    check_result = ratchet_service.check_ratchet(
        manifest=mismatched_manifest,
        ratchet_path=baseline_path,
        runs=None,
        signature_policy=SignaturePolicy.WARN,
    )
    assert check_result.warn_signature == check_result.report.has_signature_mismatch()
    assert check_result.exit_code >= 0

    rebaseline_path = tmp_path / "rebaseline.json"
    rebaseline_result = ratchet_service.rebaseline_ratchet(
        manifest=mismatched_manifest,
        ratchet_path=baseline_path,
        runs=None,
        generated_at="2025-02-02T00:00:00Z",
        output_path=rebaseline_path,
        force=True,
    )
    assert rebaseline_result.output_path == rebaseline_path
    assert rebaseline_path.exists()

    update_result = ratchet_service.update_ratchet(
        manifest=mismatched_manifest,
        ratchet_path=rebaseline_path,
        runs=None,
        generated_at="2025-03-03T00:00:00Z",
        target_overrides={"error": 0, "pyright:current.warning": 5},
        output_path=None,
        force=True,
        dry_run=True,
    )
    assert not update_result.wrote_file
    targets = update_result.updated.runs[RunId("pyright:current")].targets
    assert targets[SeverityLevel.ERROR] == 0
    assert targets[SeverityLevel.WARNING] == 5


def test_ratchet_operations_require_paths(tmp_path: Path) -> None:
    manifest = _detailed_manifest(per_file_counts={"src/bar.py": 1})
    with pytest.raises(RatchetPathRequiredError):
        _ = ratchet_service.check_ratchet(
            manifest=manifest,
            ratchet_path=None,
            runs=None,
            signature_policy=SignaturePolicy.FAIL,
        )
    with pytest.raises(RatchetPathRequiredError):
        _ = ratchet_service.update_ratchet(
            manifest=manifest,
            ratchet_path=None,
            runs=None,
            generated_at="now",
            target_overrides=None,
            output_path=None,
            force=True,
            dry_run=True,
        )
    with pytest.raises(RatchetPathRequiredError):
        _ = ratchet_service.rebaseline_ratchet(
            manifest=manifest,
            ratchet_path=None,
            runs=None,
            generated_at="now",
            output_path=tmp_path / "out.json",
            force=True,
        )


def test_split_target_mapping_and_apply_overrides() -> None:
    global_targets, per_run = ratchet_service.split_target_mapping({
        "error": -1,
        "pyright:current.warning": 2,
        "pyright:current.error": 3,
        "   ": 4,
    })
    assert global_targets[SeverityLevel.ERROR] == 0
    assert per_run["pyright:current"][SeverityLevel.WARNING] == 2

    model = RatchetModel.model_validate({
        "generatedAt": "2025-01-01T00:00:00Z",
        "manifestPath": None,
        "projectRoot": None,
        "runs": {
            "pyright:current": {
                "severities": [SeverityLevel.ERROR.value],
                "paths": {},
                "targets": {SeverityLevel.ERROR.value: 1},
            }
        },
    })
    ratchet_service.apply_target_overrides(model, {"error": 5, "pyright:current.warning": 3})
    targets = model.runs[RunId("pyright:current")].targets
    assert targets[SeverityLevel.ERROR] == 5
    assert targets[SeverityLevel.WARNING] == 3


def test_describe_ratchet_returns_snapshot(tmp_path: Path) -> None:
    snapshot = ratchet_service.describe_ratchet(
        manifest_path=tmp_path / "manifest.json",
        ratchet_path=None,
        runs=[RunId("pyright:current")],
        severities=[SeverityLevel.ERROR],
        targets={"error": 0},
        signature_policy=SignaturePolicy.FAIL,
        limit=10,
        summary_only=True,
    )
    assert snapshot.manifest_path == tmp_path / "manifest.json"
    assert snapshot.severities == (SeverityLevel.ERROR,)
    assert snapshot.targets == {"error": 0}


def test_update_ratchet_writes_file(tmp_path: Path) -> None:
    manifest = _detailed_manifest(per_file_counts={"src/baz.py": 1})
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("", encoding="utf-8")
    baseline = tmp_path / "baseline.json"
    ratchet_service.init_ratchet(
        manifest=manifest,
        runs=None,
        manifest_path=manifest_path,
        severities=None,
        targets=None,
        output_path=baseline,
        force=True,
    )
    updated_path = tmp_path / "updated.json"
    result = ratchet_service.update_ratchet(
        manifest=manifest,
        ratchet_path=baseline,
        runs=None,
        generated_at="2025-04-04T00:00:00Z",
        target_overrides=None,
        output_path=updated_path,
        force=True,
        dry_run=False,
    )
    assert result.wrote_file
    assert result.output_path == updated_path
    assert updated_path.exists()
