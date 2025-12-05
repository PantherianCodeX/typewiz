# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Ratchet Summary."""

from __future__ import annotations

import pytest

from typewiz.core.model_types import Mode, SeverityLevel
from typewiz.core.type_aliases import RunId
from typewiz.ratchet.models import EngineSignaturePayloadWithHash
from typewiz.ratchet.summary import RatchetFinding, RatchetReport, RatchetRunReport

pytestmark = [pytest.mark.unit, pytest.mark.ratchet]


def _signature_payload(hash_value: str) -> EngineSignaturePayloadWithHash:
    return EngineSignaturePayloadWithHash(tool="pyright", mode=Mode.FULL, engineOptions={}, hash=hash_value)


def test_run_report_format_lines_includes_signature_details() -> None:
    finding = RatchetFinding(path="pkg", severity=SeverityLevel.ERROR, allowed=1, actual=3)
    report = RatchetRunReport(
        run_id=RunId("pyright:full"),
        severities=[SeverityLevel.ERROR],
        violations=[finding],
        improvements=[],
        signature_matches=False,
        expected_signature=_signature_payload("abc"),
        actual_signature=_signature_payload("def"),
    )

    lines = report.format_lines(ignore_signature=False, limit=1, summary_only=False)
    assert any("signature-mismatch" in line for line in lines)
    assert any("expected" in line.lower() for line in lines)


def test_run_report_summary_only_lists_counts() -> None:
    improvement = RatchetFinding(path="pkg", severity=SeverityLevel.ERROR, allowed=3, actual=2)
    report = RatchetRunReport(
        run_id=RunId("pyright:current"),
        severities=[SeverityLevel.ERROR],
        violations=[],
        improvements=[improvement],
    )

    lines = report.format_lines(ignore_signature=True, limit=None, summary_only=True)
    assert any("summary" in line for line in lines)
    assert any("improvements=1" in line.replace(" ", "") for line in lines)


def test_ratchet_report_exit_code_counts_signature_mismatch() -> None:
    violation = RatchetFinding(path="pkg", severity=SeverityLevel.ERROR, allowed=0, actual=1)
    run_report = RatchetRunReport(
        run_id=RunId("pyright:current"),
        severities=[SeverityLevel.ERROR],
        violations=[violation],
        signature_matches=False,
    )
    report = RatchetReport(runs=[run_report])

    assert report.exit_code(ignore_signature=False) == 1
    assert report.exit_code(ignore_signature=True) == 1
