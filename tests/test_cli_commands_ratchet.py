from __future__ import annotations

from argparse import Namespace
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from typewiz.cli.commands import ratchet as ratchet_cmd
from typewiz.cli.commands.ratchet import RatchetContext, handle_info, handle_init, handle_update
from typewiz.config import RatchetConfig
from typewiz.model_types import SignaturePolicy
from typewiz.ratchet.models import RatchetModel, RatchetRunBudgetModel
from typewiz.ratchet.summary import RatchetFinding, RatchetReport, RatchetRunReport
from typewiz.typed_manifest import ManifestData


def _make_context(
    project_root: Path,
    *,
    manifest_payload: ManifestData | None = None,
    ratchet_path: Path | None = None,
    runs: list[str] | None = None,
    signature_policy: SignaturePolicy = SignaturePolicy.FAIL,
    limit: int | None = None,
    summary_only: bool = False,
    config: RatchetConfig | None = None,
) -> RatchetContext:
    payload = (
        manifest_payload
        if manifest_payload is not None
        else cast(ManifestData, {"generatedAt": "2025-01-01T00:00:00Z", "runs": []})
    )
    cfg = config or RatchetConfig()
    manifest_path = project_root / "typing_audit.json"
    return RatchetContext(
        project_root=project_root,
        config=cfg,
        manifest_path=manifest_path,
        ratchet_path=ratchet_path,
        manifest_payload=payload,
        runs=runs,
        signature_policy=signature_policy,
        limit=limit,
        summary_only=summary_only,
    )


def test_ratchet_context_generated_at_prefers_manifest(tmp_path: Path) -> None:
    context = _make_context(tmp_path, manifest_payload={"generatedAt": "2024-07-01T08:00:00Z"})
    assert context.generated_at == "2024-07-01T08:00:00Z"


def test_ratchet_context_generated_at_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_timestamp() -> str:
        return "NOW"

    monkeypatch.setattr(ratchet_cmd, "current_timestamp", fake_timestamp)
    context = _make_context(tmp_path, manifest_payload={})
    assert context.generated_at == "NOW"


def test_handle_init_writes_ratchet_and_applies_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ratchet.json"
    captured_keywords: dict[str, Any] = {}

    def fake_build_from_manifest(**kwargs: Any) -> dict[str, Any]:
        captured_keywords.update(kwargs)
        return {"ratchet": "baseline"}

    write_calls: list[Path] = []

    def fake_write(path: Path, model: dict[str, Any]) -> None:
        write_calls.append(path)
        assert model == {"ratchet": "baseline"}

    monkeypatch.setattr(ratchet_cmd, "ratchet_build_from_manifest", fake_build_from_manifest)
    monkeypatch.setattr(ratchet_cmd, "write_ratchet", fake_write)

    config = RatchetConfig()
    config.targets = {"warning": 2}
    context = _make_context(tmp_path, config=config)

    args = Namespace(
        output=output_path,
        force=True,
        severities="errors,warnings",
        targets=["errors=1"],
    )

    exit_code = handle_init(context, args)
    assert exit_code == 0
    assert write_calls == [output_path]
    assert captured_keywords["severities"] == ["error", "warning"]
    assert captured_keywords["targets"] == {"warning": 2, "errors": 1}
    assert captured_keywords["manifest_path"] == str(context.manifest_path)


def test_handle_init_refuses_overwrite_without_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ratchet.json"
    _ = output_path.write_text("{}", encoding="utf-8")

    def fail_build(**_: Any) -> None:
        raise AssertionError("ratchet_build_from_manifest should not be called")

    monkeypatch.setattr(ratchet_cmd, "ratchet_build_from_manifest", fail_build)

    context = _make_context(tmp_path)
    args = Namespace(output=output_path, force=False, severities=None, targets=[])
    exit_code = handle_init(context, args)
    assert exit_code == 1


def test_handle_update_dry_run_skips_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ratchet_path = tmp_path / "ratchet.json"
    context = _make_context(tmp_path, ratchet_path=ratchet_path)

    minimum_model = RatchetModel.model_validate(
        {
            "generatedAt": "2025-01-01T00:00:00Z",
            "manifestPath": str(tmp_path / "typing_audit.json"),
            "projectRoot": str(tmp_path),
            "runs": {"pyright:current": {"severities": ["error"], "paths": {}, "targets": {}}},
        },
    )

    def fake_load_ratchet(path: Path) -> RatchetModel:
        assert path == ratchet_path
        return minimum_model

    monkeypatch.setattr(ratchet_cmd, "load_ratchet", fake_load_ratchet)
    applied_targets: dict[str, int] | None = None

    def fake_apply_target_overrides(model: RatchetModel, targets: dict[str, int]) -> None:
        nonlocal applied_targets
        applied_targets = targets
        model.runs.setdefault(
            "pyright:current",
            RatchetRunBudgetModel(severities=["error"], paths={}, targets={}),
        ).targets.update(targets)

    def fake_compare_manifest(**_: Any) -> RatchetReport:
        finding = RatchetFinding(path="pkg", severity="error", allowed=1, actual=2)
        run_report = RatchetRunReport(
            run_id="pyright:current",
            severities=["error"],
            violations=[finding],
        )
        return RatchetReport(runs=[run_report])

    def fake_apply_auto_update(**_: Any) -> RatchetModel:
        return RatchetModel.model_validate(
            {
                "generatedAt": "2025-01-02T00:00:00Z",
                "manifestPath": str(tmp_path / "typing_audit.json"),
                "projectRoot": str(tmp_path),
                "runs": {
                    "pyright:current": {
                        "severities": ["error"],
                        "paths": {"pkg": {"severities": {"error": 2}}},
                        "targets": {"errors": 5},
                    },
                },
            },
        )

    monkeypatch.setattr(ratchet_cmd, "apply_target_overrides", fake_apply_target_overrides)
    monkeypatch.setattr(ratchet_cmd, "ratchet_compare_manifest", fake_compare_manifest)
    monkeypatch.setattr(ratchet_cmd, "ratchet_apply_auto_update", fake_apply_auto_update)

    def fail_write(path: Path, model: dict[str, Any]) -> None:  # pragma: no cover - guard
        raise AssertionError(f"write_ratchet should not be called: {(path, model)}")

    monkeypatch.setattr(ratchet_cmd, "write_ratchet", fail_write)

    args = Namespace(
        targets=["errors=5"], dry_run=True, output=None, limit=None, summary_only=False
    )
    exit_code = handle_update(context, args)

    assert exit_code == 0
    assert applied_targets == {"errors": 5}
    captured = capsys.readouterr().out
    assert "[typewiz] Dry-run mode; ratchet not written." in captured


def test_handle_info_reports_configuration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = RatchetConfig()
    config.targets = {"error": 1}
    context = _make_context(
        tmp_path,
        config=config,
        ratchet_path=tmp_path / "ratchet.json",
        runs=["pyright:current"],
        limit=5,
        summary_only=True,
    )

    exit_code = handle_info(context)
    assert exit_code == 0

    output = capsys.readouterr().out
    assert "ratchet configuration summary" in output.lower()
    assert "runs: pyright:current" in output
    assert "target[error] = 1" in output
    assert "display limit: 5" in output
    assert "summary-only: yes" in output


def test_execute_ratchet_unknown_action_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Lightweight stubs to avoid touching the filesystem or real configs.
    fake_config = RatchetConfig()

    def fake_load_config(_: object) -> Namespace:
        return Namespace(ratchet=fake_config)

    def fake_project_root(_: object) -> Path:
        return Path("/tmp/project")

    def fake_discover_manifest(
        _project_root: Path,
        *,
        explicit: Path | None,
        configured: Path | None,
    ) -> Path:
        assert explicit is None
        assert configured is None
        return Path("/tmp/manifest.json")

    def fake_discover_ratchet(
        _project_root: Path,
        *,
        explicit: Path | None,
        configured: Path | None,
        require_exists: bool,
    ) -> Path:
        assert require_exists is False
        return Path("/tmp/ratchet.json")

    def fake_load_manifest(_path: Path) -> ManifestData:
        return cast(ManifestData, {"generatedAt": "2024-01-01", "runs": []})

    def fake_resolve_runs(
        cli: Sequence[str] | None, config_runs: Sequence[str]
    ) -> list[str] | None:
        return list(cli or config_runs)

    def passthrough_policy(arg: Any, default: SignaturePolicy) -> SignaturePolicy:
        if arg is None:
            return default
        return SignaturePolicy.from_str(str(arg))

    def passthrough_two(arg: Any, default: Any) -> Any:
        return arg if arg is not None else default

    def fake_echo(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(ratchet_cmd, "load_config", fake_load_config)
    monkeypatch.setattr(ratchet_cmd, "resolve_project_root", fake_project_root)
    monkeypatch.setattr(ratchet_cmd, "discover_manifest_path", fake_discover_manifest)
    monkeypatch.setattr(ratchet_cmd, "discover_ratchet_path", fake_discover_ratchet)
    monkeypatch.setattr(ratchet_cmd, "load_ratchet_manifest", fake_load_manifest)
    monkeypatch.setattr(ratchet_cmd, "resolve_runs", fake_resolve_runs)
    monkeypatch.setattr(ratchet_cmd, "resolve_signature_policy", passthrough_policy)
    monkeypatch.setattr(ratchet_cmd, "resolve_limit", passthrough_two)
    monkeypatch.setattr(ratchet_cmd, "resolve_summary_only", passthrough_two)
    monkeypatch.setattr(ratchet_cmd, "echo", fake_echo)

    args = Namespace(action="invalid", manifest=None, ratchet=None)

    with pytest.raises(SystemExit):
        _ = ratchet_cmd.execute_ratchet(args)
