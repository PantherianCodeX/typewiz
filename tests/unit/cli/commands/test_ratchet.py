# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for CLI Commands Ratchet."""

from __future__ import annotations

import argparse
import tempfile
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from typewiz.cli.commands import ratchet as ratchet_cmd
from typewiz.cli.commands.ratchet import (
    RatchetContext,
    handle_check,
    handle_info,
    handle_init,
    handle_rebaseline,
    handle_update,
)
from typewiz.config import Config, RatchetConfig
from typewiz.core.model_types import RatchetAction, SeverityLevel, SignaturePolicy
from typewiz.core.type_aliases import RunId
from typewiz.manifest.versioning import CURRENT_MANIFEST_VERSION
from typewiz.ratchet.models import RatchetModel
from typewiz.ratchet.summary import RatchetFinding, RatchetReport, RatchetRunReport
from typewiz.services.ratchet import (
    RatchetCheckResult,
    RatchetInitResult,
    RatchetRebaselineResult,
    RatchetServiceError,
    RatchetUpdateResult,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typewiz.manifest.typed import ManifestData

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.ratchet]


@dataclass(slots=True)
class _DispatchScenario:
    action: str
    handler_name: str
    expects_args: bool


def _make_context(  # noqa: PLR0913  # JUSTIFIED: helper mirrors RatchetContext fields for clarity in tests
    project_root: Path,
    *,
    manifest_payload: ManifestData | None = None,
    ratchet_path: Path | None = None,
    runs: list[RunId] | None = None,
    signature_policy: SignaturePolicy = SignaturePolicy.FAIL,
    limit: int | None = None,
    summary_only: bool = False,
    config: RatchetConfig | None = None,
) -> RatchetContext:
    payload = (
        manifest_payload
        if manifest_payload is not None
        else cast(
            "ManifestData",
            {
                "generatedAt": "2025-01-01T00:00:00Z",
                "schemaVersion": CURRENT_MANIFEST_VERSION,
                "runs": [],
            },
        )
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


def _make_report(
    *,
    signature_matches: bool = True,
    violations: list[RatchetFinding] | None = None,
) -> RatchetReport:
    run = RatchetRunReport(
        run_id=RunId("pyright:current"),
        severities=[SeverityLevel.ERROR],
        violations=violations or [],
        signature_matches=signature_matches,
    )
    return RatchetReport(runs=[run])


def test_ratchet_context_generated_at_prefers_manifest(tmp_path: Path) -> None:
    context = _make_context(
        tmp_path,
        manifest_payload={
            "generatedAt": "2024-07-01T08:00:00Z",
            "schemaVersion": CURRENT_MANIFEST_VERSION,
        },
    )
    assert context.generated_at == "2024-07-01T08:00:00Z"


def test_ratchet_context_generated_at_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_timestamp() -> str:
        return "NOW"

    monkeypatch.setattr(ratchet_cmd, "current_timestamp", fake_timestamp)
    context = _make_context(tmp_path, manifest_payload={"schemaVersion": CURRENT_MANIFEST_VERSION})
    assert context.generated_at == "NOW"


def test_handle_init_writes_ratchet_and_applies_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ratchet.json"
    captured_keywords: dict[str, object] = {}
    baseline_model = RatchetModel.model_validate(
        {
            "generatedAt": "2025-01-01T00:00:00Z",
            "manifestPath": str(tmp_path / "typing_audit.json"),
            "projectRoot": str(tmp_path),
            "runs": {},
        },
    )

    def fake_init_ratchet(**kwargs: object) -> RatchetInitResult:
        captured_keywords.update(kwargs)
        return RatchetInitResult(model=baseline_model, output_path=output_path)

    monkeypatch.setattr(ratchet_cmd, "init_ratchet", fake_init_ratchet)

    config = RatchetConfig()
    config.targets = {"warning": 2}
    context = _make_context(tmp_path, config=config)

    args = Namespace(
        output=output_path,
        force=True,
        severities="error,warning",
        targets=["error=1"],
    )

    exit_code = handle_init(context, args)
    assert exit_code == 0
    assert captured_keywords["output_path"] == output_path
    assert captured_keywords["force"] is True
    assert captured_keywords["severities"] == [SeverityLevel.ERROR, SeverityLevel.WARNING]
    assert captured_keywords["targets"] == {SeverityLevel.WARNING: 2, SeverityLevel.ERROR: 1}
    assert captured_keywords["manifest_path"] == context.manifest_path


def test_handle_init_refuses_overwrite_without_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ratchet.json"

    def fail_init(**_: object) -> None:
        raise ratchet_cmd.RatchetFileExistsError(output_path)

    monkeypatch.setattr(ratchet_cmd, "init_ratchet", fail_init)

    context = _make_context(tmp_path)
    args = Namespace(output=output_path, force=False, severities=None, targets=[])
    exit_code = handle_init(context, args)
    assert exit_code == 1


def test_handle_init_defaults_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_init_ratchet(**kwargs: object) -> RatchetInitResult:
        captured.update(kwargs)
        dummy_model = RatchetModel.model_validate(
            {
                "generatedAt": "2025-01-01T00:00:00Z",
                "manifestPath": str(tmp_path / "typing_audit.json"),
                "projectRoot": str(tmp_path),
                "runs": {},
            },
        )
        output_path = cast("Path", kwargs["output_path"])
        return RatchetInitResult(model=dummy_model, output_path=output_path)

    monkeypatch.setattr(ratchet_cmd, "init_ratchet", fake_init_ratchet)
    context = _make_context(tmp_path, ratchet_path=None)
    args = Namespace(output=None, severities=None, targets=[], force=False)

    exit_code = handle_init(context, args)
    assert exit_code == 0
    assert captured["output_path"] == (tmp_path / ".typewiz" / "ratchet.json").resolve()


def test_handle_update_dry_run_skips_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ratchet_path = tmp_path / "ratchet.json"
    context = _make_context(tmp_path, ratchet_path=ratchet_path)

    report = RatchetReport(
        runs=[
            RatchetRunReport(
                run_id=RunId("pyright:current"),
                severities=[SeverityLevel.ERROR],
                violations=[RatchetFinding(path="pkg", severity=SeverityLevel.ERROR, allowed=1, actual=2)],
            ),
        ],
    )
    captured_kwargs: dict[str, object] = {}

    def fake_update_ratchet(**kwargs: object) -> RatchetUpdateResult:
        captured_kwargs.update(kwargs)
        dummy_model = RatchetModel.model_validate(
            {
                "generatedAt": "2025-01-02T00:00:00Z",
                "manifestPath": str(tmp_path / "typing_audit.json"),
                "projectRoot": str(tmp_path),
                "runs": {},
            },
        )
        return RatchetUpdateResult(
            report=report,
            updated=dummy_model,
            output_path=None,
            wrote_file=False,
        )

    monkeypatch.setattr(ratchet_cmd, "update_ratchet", fake_update_ratchet)

    args = Namespace(targets=["error=5"], dry_run=True, output=None, limit=None, summary_only=False)
    exit_code = handle_update(context, args)

    assert exit_code == 0
    assert captured_kwargs["target_overrides"] == {"error": 5}
    captured = capsys.readouterr().out
    assert "[typewiz] Dry-run mode; ratchet not written." in captured


def test_handle_update_returns_error_on_service_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context = _make_context(tmp_path)

    def boom(**_: object) -> RatchetUpdateResult:
        msg = "update failed"
        raise RatchetServiceError(msg)

    monkeypatch.setattr(ratchet_cmd, "update_ratchet", boom)
    args = Namespace(targets=[], dry_run=False, output=None, limit=None, summary_only=False, force=False)
    exit_code = handle_update(context, args)
    assert exit_code == 1


def test_handle_update_reports_written_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    context = _make_context(tmp_path, ratchet_path=tmp_path / "ratchet.json")
    output_path = tmp_path / "ratchet.json"

    def fake_update(**_: object) -> RatchetUpdateResult:
        dummy_model = RatchetModel.model_validate(
            {
                "generatedAt": "2025-02-01T00:00:00Z",
                "manifestPath": str(context.manifest_path),
                "projectRoot": str(tmp_path),
                "runs": {},
            },
        )
        return RatchetUpdateResult(
            report=_make_report(),
            updated=dummy_model,
            output_path=output_path,
            wrote_file=True,
        )

    monkeypatch.setattr(ratchet_cmd, "update_ratchet", fake_update)
    args = Namespace(targets=[], dry_run=False, output=None, limit=None, summary_only=False, force=False)
    exit_code = handle_update(context, args)
    assert exit_code == 0
    assert "Ratchet updated" in capsys.readouterr().out


def test_handle_check_outputs_json_and_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    context = _make_context(tmp_path)
    report = _make_report(signature_matches=False, violations=[])

    def fake_check_ratchet(**_: object) -> RatchetCheckResult:
        return RatchetCheckResult(
            report=report,
            ignore_signature=False,
            warn_signature=True,
            exit_code=1,
        )

    monkeypatch.setattr(ratchet_cmd, "check_ratchet", fake_check_ratchet)
    args = Namespace(format="json")

    exit_code = handle_check(context, args)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert '"runs":' in captured.out
    assert "Signature mismatch" in captured.err


def test_handle_check_returns_error_when_service_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context = _make_context(tmp_path)

    def boom(**_: object) -> RatchetCheckResult:
        msg = "failure"
        raise RatchetServiceError(msg)

    monkeypatch.setattr(ratchet_cmd, "check_ratchet", boom)
    args = Namespace(format="json")
    exit_code = handle_check(context, args)
    assert exit_code == 1


def test_handle_check_outputs_table_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    context = _make_context(tmp_path, limit=2, summary_only=True)

    class StubReport:
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[tuple[bool, int | None, bool]] = []

        def format_lines(self, *, ignore_signature: bool, limit: int | None, summary_only: bool) -> list[str]:
            self.calls.append((ignore_signature, limit, summary_only))
            return ["line-a", "line-b"]

        def to_payload(self) -> dict[str, object]:
            return {}

        def has_signature_mismatch(self) -> bool:
            return False

        def has_violations(self) -> bool:
            return False

    stub_report = StubReport()

    def fake_check(**_: object) -> RatchetCheckResult:
        return RatchetCheckResult(
            report=cast("RatchetReport", stub_report),
            ignore_signature=True,
            warn_signature=False,
            exit_code=0,
        )

    monkeypatch.setattr(ratchet_cmd, "check_ratchet", fake_check)
    args = Namespace(format="table")

    exit_code = handle_check(context, args)
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "line-a" in out
    assert stub_report.calls == [(True, 2, True)]


def test_handle_info_reports_configuration(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = RatchetConfig()
    config.targets = {"error": 1}
    context = _make_context(
        tmp_path,
        config=config,
        ratchet_path=tmp_path / "ratchet.json",
        runs=[RunId("pyright:current")],
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


def test_handle_info_displays_absence_of_targets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    context = _make_context(tmp_path, config=RatchetConfig())
    exit_code = handle_info(context)
    assert exit_code == 0
    assert "targets: <none>" in capsys.readouterr().out


def test_handle_rebaseline_uses_resolved_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context = _make_context(tmp_path, ratchet_path=tmp_path / "ratchet.json")
    resolved_output = tmp_path / "out" / "ratchet.json"
    captured: dict[str, object] = {}

    def fake_rebaseline(**kwargs: object) -> RatchetRebaselineResult:
        captured.update(kwargs)
        dummy_model = RatchetModel.model_validate(
            {
                "generatedAt": "2025-01-03T00:00:00Z",
                "manifestPath": str(context.manifest_path),
                "projectRoot": str(tmp_path),
                "runs": {},
            },
        )
        return RatchetRebaselineResult(refreshed=dummy_model, output_path=resolved_output)

    monkeypatch.setattr(ratchet_cmd, "rebaseline_ratchet", fake_rebaseline)

    args = Namespace(output=Path("out/ratchet.json"), force=True)
    exit_code = handle_rebaseline(context, args)
    assert exit_code == 0
    assert captured["output_path"] == resolved_output
    assert captured["force"] is True


def test_handle_rebaseline_requires_existing_path(tmp_path: Path) -> None:
    context = _make_context(tmp_path, ratchet_path=None)
    with pytest.raises(SystemExit, match=r".*"):
        _ = handle_rebaseline(context, Namespace(output=None, force=False))


def test_handle_rebaseline_reports_service_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context = _make_context(tmp_path, ratchet_path=tmp_path / "ratchet.json")

    def boom(**_: object) -> RatchetRebaselineResult:
        msg = "cannot rebaseline"
        raise RatchetServiceError(msg)

    monkeypatch.setattr(ratchet_cmd, "rebaseline_ratchet", boom)
    exit_code = handle_rebaseline(context, Namespace(output=None, force=False))
    assert exit_code == 1


def test_execute_ratchet_unknown_action_raises(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: C901  # JUSTIFIED: high-level wiring test exercises many stubbed collaborators in one integration-style flow
    # Lightweight stubs to avoid touching the filesystem or real configs.
    fake_config = Config()

    def fake_load_config(_: object) -> Config:
        return fake_config

    tmp_root = Path(tempfile.gettempdir()) / "typewiz-cli"

    def fake_project_root(_: object) -> Path:
        return tmp_root / "project"

    def fake_discover_manifest(
        _project_root: Path,
        *,
        explicit: Path | None,
        configured: Path | None,
    ) -> Path:
        assert explicit is None
        assert configured is None
        return tmp_root / "manifest.json"

    def fake_discover_ratchet(
        _project_root: Path,
        *,
        explicit: Path | None,
        configured: Path | None,
        require_exists: bool,
    ) -> Path:
        assert explicit is None
        assert configured is None
        assert require_exists is False
        return tmp_root / "ratchet.json"

    def fake_load_manifest(_path: Path) -> ManifestData:
        return cast(
            "ManifestData",
            {"generatedAt": "2024-01-01", "schemaVersion": CURRENT_MANIFEST_VERSION, "runs": []},
        )

    def fake_resolve_runs(cli: Sequence[str | RunId] | None, config_runs: Sequence[str | RunId]) -> list[RunId] | None:
        values = cli or config_runs
        if not values:
            return None
        return [RunId(str(value)) for value in values]

    def passthrough_policy(arg: SignaturePolicy | str | None, default: SignaturePolicy) -> SignaturePolicy:
        if arg is None:
            return default
        return arg if isinstance(arg, SignaturePolicy) else SignaturePolicy.from_str(str(arg))

    def passthrough_limit(arg: int | None, default: int | None) -> int | None:
        return arg if arg is not None else default

    def passthrough_summary_only(*, cli_summary: bool, config_summary: bool) -> bool:
        return cli_summary or config_summary

    def fake_echo(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(ratchet_cmd, "load_config", fake_load_config)
    monkeypatch.setattr(ratchet_cmd, "resolve_project_root", fake_project_root)
    monkeypatch.setattr(ratchet_cmd, "discover_manifest_path", fake_discover_manifest)
    monkeypatch.setattr(ratchet_cmd, "discover_ratchet_path", fake_discover_ratchet)
    monkeypatch.setattr(ratchet_cmd, "load_ratchet_manifest", fake_load_manifest)
    monkeypatch.setattr(ratchet_cmd, "resolve_runs", fake_resolve_runs)
    monkeypatch.setattr(ratchet_cmd, "resolve_signature_policy", passthrough_policy)
    monkeypatch.setattr(ratchet_cmd, "resolve_limit", passthrough_limit)
    monkeypatch.setattr(ratchet_cmd, "resolve_summary_only", passthrough_summary_only)
    monkeypatch.setattr(ratchet_cmd, "echo", fake_echo)

    args = Namespace(action="invalid", manifest=None, ratchet=None)

    with pytest.raises(SystemExit, match=r".*"):
        _ = ratchet_cmd.execute_ratchet(args)


def test_register_ratchet_command_builds_subcommands(tmp_path: Path) -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    ratchet_cmd.register_ratchet_command(subcommands)
    manifest_path = tmp_path / "typing_audit.json"
    _ = manifest_path.write_text("{}", encoding="utf-8")
    args = parser.parse_args([
        "ratchet",
        "init",
        "--manifest",
        str(manifest_path),
    ])
    assert args.action == "init"


@pytest.mark.parametrize(
    "scenario",
    [
        _DispatchScenario(RatchetAction.INIT.value, "handle_init", expects_args=True),
        _DispatchScenario(RatchetAction.CHECK.value, "handle_check", expects_args=True),
        _DispatchScenario(RatchetAction.UPDATE.value, "handle_update", expects_args=True),
        _DispatchScenario(
            RatchetAction.REBASELINE_SIGNATURE.value,
            "handle_rebaseline",
            expects_args=True,
        ),
        _DispatchScenario(RatchetAction.INFO.value, "handle_info", expects_args=False),
    ],
)
def test_execute_ratchet_dispatches_actions(  # noqa: C901  # JUSTIFIED: dispatch table wired once and exercised via parametrisation for multiple actions
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: _DispatchScenario,
) -> None:
    fake_config = Config()

    def fake_load_config(_: object) -> Config:
        return fake_config

    manifest_path = tmp_path / "typing_audit.json"
    _ = manifest_path.write_text("{}", encoding="utf-8")

    def fake_project_root(_: object) -> Path:
        return tmp_path

    def fake_discover_manifest(project_root: Path, *, explicit: Path | None, configured: Path | None) -> Path:
        assert isinstance(project_root, Path)
        assert explicit is None or isinstance(explicit, Path)
        assert configured is None or isinstance(configured, Path)
        return manifest_path

    def fake_discover_ratchet(
        project_root: Path,
        *,
        explicit: Path | None,
        configured: Path | None,
        require_exists: bool,
    ) -> Path:
        assert isinstance(project_root, Path)
        assert explicit is None or isinstance(explicit, Path)
        assert configured is None or isinstance(configured, Path)
        assert isinstance(require_exists, bool)
        return tmp_path / "ratchet.json"

    def fake_load_manifest(_: Path) -> ManifestData:
        return cast("ManifestData", {"generatedAt": "2024-01-01", "schemaVersion": CURRENT_MANIFEST_VERSION})

    def passthrough_runs(
        cli: Sequence[str | RunId] | None, config: Sequence[str | RunId]
    ) -> Sequence[str | RunId] | None:
        return cli or config

    def passthrough_signature_policy(value: str | None, default: SignaturePolicy) -> SignaturePolicy:
        assert value is None or isinstance(value, str)
        return default

    def passthrough_limit(value: int | None, default: int | None) -> int | None:
        assert value is None or isinstance(value, int)
        return default

    def passthrough_summary_only(*, cli_summary: bool, config_summary: bool) -> bool:
        return bool(cli_summary) or config_summary

    def noop_echo(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(ratchet_cmd, "load_config", fake_load_config)
    monkeypatch.setattr(ratchet_cmd, "resolve_project_root", fake_project_root)
    monkeypatch.setattr(ratchet_cmd, "discover_manifest_path", fake_discover_manifest)
    monkeypatch.setattr(ratchet_cmd, "discover_ratchet_path", fake_discover_ratchet)
    monkeypatch.setattr(ratchet_cmd, "load_ratchet_manifest", fake_load_manifest)
    monkeypatch.setattr(ratchet_cmd, "resolve_runs", passthrough_runs)
    monkeypatch.setattr(ratchet_cmd, "resolve_signature_policy", passthrough_signature_policy)
    monkeypatch.setattr(ratchet_cmd, "resolve_limit", passthrough_limit)
    monkeypatch.setattr(ratchet_cmd, "resolve_summary_only", passthrough_summary_only)
    monkeypatch.setattr(ratchet_cmd, "echo", noop_echo)

    called: dict[str, object] = {}

    def fake_handler(context: RatchetContext, args: Namespace | None = None) -> int:
        called["context"] = context
        called["args"] = args
        return 7

    def fake_handler_no_args(context: RatchetContext) -> int:
        return fake_handler(context, None)

    if scenario.expects_args:
        monkeypatch.setattr(ratchet_cmd, scenario.handler_name, fake_handler)
    else:
        monkeypatch.setattr(ratchet_cmd, scenario.handler_name, fake_handler_no_args)

    args = Namespace(action=scenario.action, manifest=None, ratchet=None, summary_only=False)
    exit_code = ratchet_cmd.execute_ratchet(args)
    assert exit_code == 7
    assert isinstance(called["context"], RatchetContext)
    if scenario.expects_args:
        assert isinstance(called["args"], Namespace)
    else:
        assert called["args"] is None
