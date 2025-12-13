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

"""Unit tests for CLI Commands Ratchet."""

from __future__ import annotations

import argparse
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from ratchetr.cli.commands import ratchet as ratchet_cmd
from ratchetr.cli.commands.ratchet import (
    RatchetContext,
    handle_check,
    handle_info,
    handle_init,
    handle_rebaseline,
    handle_update,
)
from ratchetr.cli.helpers import CLIContext, StdoutFormat
from ratchetr.config import RatchetConfig
from ratchetr.core.model_types import RatchetAction, SeverityLevel, SignaturePolicy
from ratchetr.core.type_aliases import RunId
from ratchetr.manifest.versioning import CURRENT_MANIFEST_VERSION
from ratchetr.ratchet.models import RatchetModel
from ratchetr.ratchet.summary import RatchetFinding, RatchetReport, RatchetRunReport
from ratchetr.services.ratchet import (
    RatchetCheckResult,
    RatchetInitResult,
    RatchetRebaselineResult,
    RatchetServiceError,
    RatchetUpdateResult,
)

if TYPE_CHECKING:
    from ratchetr.manifest.typed import ManifestData

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.ratchet]


@dataclass(slots=True)
class _DispatchScenario:
    action: str
    handler_name: str
    expects_args: bool


# ignore JUSTIFIED: helper mirrors RatchetContext fields for realistic test contexts
# many parameters reflect the underlying dataclass shape
def _make_context(  # noqa: PLR0913
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
    assert captured["output_path"] == (tmp_path / ".ratchetr" / "ratchet.json").resolve()


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
    assert "[ratchetr] Dry-run mode; ratchet not written." in captured


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
    args = Namespace(out=StdoutFormat.JSON.value)

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
    args = Namespace(out=StdoutFormat.JSON.value)
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
            self.payload: dict[str, object] = {}
            self.signature_mismatch: bool = False
            self.violations: bool = False

        def format_lines(self, *, ignore_signature: bool, limit: int | None, summary_only: bool) -> list[str]:
            self.calls.append((ignore_signature, limit, summary_only))
            return ["line-a", "line-b"]

        def to_payload(self) -> dict[str, object]:
            return dict(self.payload)

        def has_signature_mismatch(self) -> bool:
            return self.signature_mismatch

        def has_violations(self) -> bool:
            return self.violations

    stub_report = StubReport()

    def fake_check(**_: object) -> RatchetCheckResult:
        return RatchetCheckResult(
            report=cast("RatchetReport", stub_report),
            ignore_signature=True,
            warn_signature=False,
            exit_code=0,
        )

    monkeypatch.setattr(ratchet_cmd, "check_ratchet", fake_check)
    args = Namespace(out=StdoutFormat.TEXT.value)

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


def test_execute_ratchet_unknown_action_raises(cli_context: CLIContext) -> None:
    manifest_path = cli_context.resolved_paths.manifest_path
    manifest_path.write_text(
        f'{{"schemaVersion": "{CURRENT_MANIFEST_VERSION}", "runs": []}}',
        encoding="utf-8",
    )
    args = Namespace(action="invalid", ratchet=None, out=StdoutFormat.TEXT.value, summary_only=False)

    with pytest.raises(SystemExit, match=r".*"):
        _ = ratchet_cmd.execute_ratchet(args, cli_context)


def test_register_ratchet_command_builds_subcommands() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    ratchet_cmd.register_ratchet_command(subcommands)
    args = parser.parse_args([
        "ratchet",
        "init",
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
def test_execute_ratchet_dispatches_actions(
    monkeypatch: pytest.MonkeyPatch,
    cli_context: CLIContext,
    scenario: _DispatchScenario,
) -> None:
    manifest_path = cli_context.resolved_paths.manifest_path
    manifest_path.write_text("{}", encoding="utf-8")
    ratchet_path = cli_context.resolved_paths.tool_home / "ratchet.json"
    ratchet_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        ratchet_cmd,
        "discover_manifest_or_exit",
        lambda *_args, **_kwargs: manifest_path,
    )
    monkeypatch.setattr(
        ratchet_cmd,
        "discover_ratchet_path",
        lambda *_args, **_kwargs: ratchet_path,
    )
    monkeypatch.setattr(
        ratchet_cmd,
        "load_ratchet_manifest",
        lambda _path: cast("ManifestData", {"schemaVersion": CURRENT_MANIFEST_VERSION, "runs": []}),
    )

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

    args = Namespace(action=scenario.action, ratchet=ratchet_path, out=StdoutFormat.TEXT.value, summary_only=False)
    exit_code = ratchet_cmd.execute_ratchet(args, cli_context)
    assert exit_code == 7
    assert isinstance(called["context"], RatchetContext)
    if scenario.expects_args:
        assert isinstance(called["args"], Namespace)
    else:
        assert called["args"] is None
