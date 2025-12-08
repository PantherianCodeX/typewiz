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

"""Ratchet report data structures and formatting helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from ratchetr.core.model_types import Mode, SeverityLevel

if TYPE_CHECKING:
    from collections.abc import Callable

    from ratchetr.core.type_aliases import RunId

    from .models import EngineSignaturePayloadWithHash


def _new_finding_list() -> list[RatchetFinding]:
    """Create an empty list of ratchet findings.

    Returns:
        list[RatchetFinding]: An empty list for storing ratchet findings.
    """
    return []


@dataclass(slots=True, frozen=True)
class RatchetFinding:
    """Single severity finding for a path compared against its budget."""

    path: str
    severity: SeverityLevel
    allowed: int
    actual: int

    @property
    def delta(self) -> int:
        """Compute the difference between actual and allowed diagnostics.

        Returns:
            int: The difference (actual - allowed), positive means more than allowed.
        """
        return self.actual - self.allowed

    def to_payload(
        self,
        *,
        include_delta: bool = True,
        rename_allowed: str | None = None,
    ) -> dict[str, object]:
        """Serialize the finding for JSON output.

        Args:
            include_delta (bool, optional): Whether to include the delta field. Defaults to True.
            rename_allowed (str | None, optional): Alternative name for the "allowed" field. Defaults to None.

        Returns:
            dict[str, object]: A dictionary representation of the finding.
        """
        payload: dict[str, object] = {
            "path": self.path,
            "severity": self.severity.value,
            "actual": self.actual,
        }
        allowed_key = rename_allowed or "allowed"
        payload[allowed_key] = self.allowed
        if include_delta:
            payload["delta"] = self.delta
        return payload


@dataclass(slots=True, frozen=True)
class RatchetRunReport:
    """Aggregated findings for a single tool/mode run."""

    run_id: RunId
    severities: list[SeverityLevel]
    violations: list[RatchetFinding] = field(default_factory=_new_finding_list)
    improvements: list[RatchetFinding] = field(default_factory=_new_finding_list)
    signature_matches: bool = True
    expected_signature: EngineSignaturePayloadWithHash | None = None
    actual_signature: EngineSignaturePayloadWithHash | None = None

    def has_violations(self) -> bool:
        """Check if this run has any ratchet violations.

        Returns:
            bool: True if there are violations, False otherwise.
        """
        return bool(self.violations)

    def has_signature_mismatch(self) -> bool:
        """Check if this run has a signature mismatch.

        Returns:
            bool: True if signatures don't match, False otherwise.
        """
        return not self.signature_matches

    def to_payload(self) -> dict[str, object]:
        """Serialize the run report to a dictionary payload.

        Returns:
            dict[str, object]: A dictionary representation of the run report.
        """

        def _signature_payload(
            entry: EngineSignaturePayloadWithHash | None,
        ) -> EngineSignaturePayloadWithHash | None:
            if entry is None:
                return None
            payload = dict(entry)
            mode_value = payload.get("mode")
            if isinstance(mode_value, Mode):
                payload["mode"] = mode_value.value
            return cast("EngineSignaturePayloadWithHash", payload)

        return {
            "run": self.run_id,
            "severities": [severity.value for severity in self.severities],
            "violations": [finding.to_payload() for finding in self.violations],
            "improvements": [finding.to_payload(rename_allowed="previous") for finding in self.improvements],
            "signature_matches": self.signature_matches,
            "expected_signature": _signature_payload(self.expected_signature),
            "actual_signature": _signature_payload(self.actual_signature),
        }

    def format_lines(
        self,
        *,
        ignore_signature: bool,
        limit: int | None = None,
        summary_only: bool = False,
    ) -> list[str]:
        """Format the run report as human-readable text lines.

        Args:
            ignore_signature (bool): Whether to ignore signature mismatches in the output.
            limit (int | None, optional): Maximum number of findings to display per section. Defaults to None.
            summary_only (bool, optional): If True, only show summary statistics. Defaults to False.

        Returns:
            list[str]: Formatted text lines describing the run report.
        """
        lines = [self._status_line(ignore_signature=ignore_signature)]
        if summary_only:
            lines.append(self._summary_line())
            return lines

        lines.extend(
            self._format_finding_block(
                title="Violations",
                findings=self.violations,
                limit=limit,
                formatter=self._format_violation_line,
            )
        )
        lines.extend(
            self._format_finding_block(
                title="Improvements",
                findings=self.improvements,
                limit=limit,
                formatter=self._format_improvement_line,
            )
        )
        if not ignore_signature and self.has_signature_mismatch():
            expected_hash = self.expected_signature.get("hash") if self.expected_signature else "<none>"
            actual_hash = self.actual_signature.get("hash") if self.actual_signature else "<none>"
            lines.append("  Engine signature mismatch:" + f" expected={expected_hash} actual={actual_hash}")
        return lines

    def _status_line(self, *, ignore_signature: bool) -> str:
        """Generate the status line summarizing the run result.

        Args:
            ignore_signature: Whether to ignore signature mismatches.

        Returns:
            str: A formatted status line.
        """
        status_parts: list[str] = []
        if self.violations:
            status_parts.append("violations")
        if not ignore_signature and self.has_signature_mismatch():
            status_parts.append("signature-mismatch")
        if self.improvements and not self.violations:
            status_parts.append("improved")
        if not status_parts:
            status_parts.append("clean")
        status = ",".join(status_parts)
        return f"[ratchetr] ratchet run={self.run_id} status={status}"

    def _summary_line(self) -> str:
        """Generate a summary line with counts.

        Returns:
            str: A formatted summary line with violation and improvement counts.
        """
        signature = "ok" if self.signature_matches else "mismatch"
        return (
            f"  summary: violations={len(self.violations)} improvements={len(self.improvements)} signature={signature}"
        )

    def _format_finding_block(
        self,
        *,
        title: str,
        findings: list[RatchetFinding],
        limit: int | None,
        formatter: Callable[[RatchetFinding], str],
    ) -> list[str]:
        """Format a block of findings with a title.

        Args:
            title (str): The section title (e.g., "Violations", "Improvements").
            findings (list[RatchetFinding]): The findings to format.
            limit (int | None): Maximum number of findings to display.
            formatter (Callable[[RatchetFinding], str]): Function to format individual findings.

        Returns:
            list[str]: Formatted text lines for the finding block.
        """
        if not findings:
            return [f"  {title}: none"]
        lines = [f"  {title}:"]
        lines.extend("    " + formatter(finding) for finding in self._slice_findings(findings, limit))
        return lines

    @staticmethod
    def _slice_findings(
        findings: list[RatchetFinding],
        limit: int | None,
    ) -> list[RatchetFinding]:
        """Limit the number of findings if a limit is specified.

        Args:
            findings (list[RatchetFinding]): The findings to slice.
            limit (int | None): Maximum number of findings to return, or None for all.

        Returns:
            list[RatchetFinding]: A sliced list of findings.
        """
        if limit is not None and limit > 0:
            return findings[:limit]
        return findings

    @staticmethod
    def _format_violation_line(finding: RatchetFinding) -> str:
        """Format a violation finding as a text line.

        Args:
            finding (RatchetFinding): The violation finding to format.

        Returns:
            str: A formatted text line showing the violation details.
        """
        return (
            f"{finding.path} [{finding.severity.value}] "
            f"actual={finding.actual} allowed={finding.allowed} delta=+{finding.delta}"
        )

    @staticmethod
    def _format_improvement_line(finding: RatchetFinding) -> str:
        """Format an improvement finding as a text line.

        Args:
            finding (RatchetFinding): The improvement finding to format.

        Returns:
            str: A formatted text line showing the improvement details.
        """
        return (
            f"{finding.path} [{finding.severity.value}] "
            f"previous={finding.allowed} current={finding.actual} delta={finding.delta}"
        )


@dataclass(slots=True)
class RatchetReport:
    """Top-level report containing all evaluated runs."""

    runs: list[RatchetRunReport]

    def has_violations(self) -> bool:
        """Check if any run in this report has violations.

        Returns:
            bool: True if any run has violations, False otherwise.
        """
        return any(run.has_violations() for run in self.runs)

    def has_signature_mismatch(self) -> bool:
        """Check if any run in this report has a signature mismatch.

        Returns:
            bool: True if any run has a signature mismatch, False otherwise.
        """
        return any(run.has_signature_mismatch() for run in self.runs)

    def to_payload(self) -> dict[str, object]:
        """Serialize the report to a dictionary payload.

        Returns:
            dict[str, object]: A dictionary representation of the entire report.
        """
        return {
            "runs": [run.to_payload() for run in self.runs],
            "has_violations": self.has_violations(),
        }

    def format_lines(
        self,
        *,
        ignore_signature: bool,
        limit: int | None = None,
        summary_only: bool = False,
    ) -> list[str]:
        """Format the entire report as human-readable text lines.

        Args:
            ignore_signature (bool): Whether to ignore signature mismatches in the output.
            limit (int | None, optional): Maximum number of findings to display per section. Defaults to None.
            summary_only (bool, optional): If True, only show summary statistics. Defaults to False.

        Returns:
            list[str]: Formatted text lines describing the entire report.
        """
        lines: list[str] = []
        for run in self.runs:
            lines.extend(
                run.format_lines(
                    ignore_signature=ignore_signature,
                    limit=limit,
                    summary_only=summary_only,
                )
            )
        return lines

    def exit_code(self, *, ignore_signature: bool) -> int:
        """Determine the exit code based on report findings.

        Args:
            ignore_signature (bool): Whether to ignore signature mismatches when determining exit code.

        Returns:
            int: Exit code (1 if violations or signature mismatch, 0 otherwise).
        """
        if self.has_violations():
            return 1
        if not ignore_signature and self.has_signature_mismatch():
            return 1
        return 0


__all__ = [
    "RatchetFinding",
    "RatchetReport",
    "RatchetRunReport",
]
