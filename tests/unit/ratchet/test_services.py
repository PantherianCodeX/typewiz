# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Ratchet Services."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from typewiz.core.model_types import SeverityLevel, SignaturePolicy
from typewiz.core.type_aliases import RunId
from typewiz.ratchet.models import RatchetModel
from typewiz.ratchet.summary import RatchetFinding, RatchetReport, RatchetRunReport
from typewiz.services import ratchet as ratchet_service
from typewiz.services.ratchet import (
    RatchetFileExistsError,
    RatchetPathRequiredError,
)

if TYPE_CHECKING:
    from pathlib import Path

    from typewiz.manifest.typed import ManifestData

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


def test_init_ratchet_invokes_builder_and_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(tmp_path)
    output_path = tmp_path / "ratchet.json"
    model = _ratchet_model(tmp_path)
    captured: dict[str, object] = {}

    def fake_build(**kwargs: object) -> RatchetModel:
        captured["build"] = kwargs
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
