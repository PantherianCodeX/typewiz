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

"""Unit tests for Ratchet Summary."""

from __future__ import annotations

import pytest

from ratchetr.core.model_types import Mode, SeverityLevel
from ratchetr.core.type_aliases import RunId
from ratchetr.ratchet.models import EngineSignaturePayloadWithHash
from ratchetr.ratchet.summary import RatchetFinding, RatchetReport, RatchetRunReport

pytestmark = [pytest.mark.unit, pytest.mark.ratchet]


def _signature_payload(hash_value: str) -> EngineSignaturePayloadWithHash:
    return EngineSignaturePayloadWithHash(tool="pyright", mode=Mode.TARGET, engineOptions={}, hash=hash_value)


def test_run_report_format_lines_includes_signature_details() -> None:
    finding = RatchetFinding(path="pkg", severity=SeverityLevel.ERROR, allowed=1, actual=3)
    report = RatchetRunReport(
        run_id=RunId("pyright:target"),
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
