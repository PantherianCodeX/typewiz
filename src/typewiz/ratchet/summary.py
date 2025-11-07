# Copyright (c) 2024 PantherianCodeX
"""Ratchet report data structures and formatting helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from ..model_types import Mode, SeverityLevel
from ..type_aliases import RunId
from .models import EngineSignaturePayloadWithHash


def _new_finding_list() -> list[RatchetFinding]:
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
        """Compute the difference between actual and allowed diagnostics."""

        return self.actual - self.allowed

    def to_payload(
        self,
        *,
        include_delta: bool = True,
        rename_allowed: str | None = None,
    ) -> dict[str, object]:
        """Serialise the finding for JSON output."""

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
        return bool(self.violations)

    def has_signature_mismatch(self) -> bool:
        return not self.signature_matches

    def to_payload(self) -> dict[str, object]:
        def _signature_payload(
            entry: EngineSignaturePayloadWithHash | None,
        ) -> EngineSignaturePayloadWithHash | None:
            if entry is None:
                return None
            payload = dict(entry)
            mode_value = payload.get("mode")
            if isinstance(mode_value, Mode):
                payload["mode"] = mode_value.value
            return cast(EngineSignaturePayloadWithHash, payload)

        return {
            "run": self.run_id,
            "severities": [severity.value for severity in self.severities],
            "violations": [finding.to_payload() for finding in self.violations],
            "improvements": [
                finding.to_payload(rename_allowed="previous") for finding in self.improvements
            ],
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
        lines = [f"[typewiz] ratchet run={self.run_id} status={status}"]
        if summary_only:
            summary_line = (
                "  summary: violations={violations} improvements={improvements} signature={signature}"
            ).format(
                violations=len(self.violations),
                improvements=len(self.improvements),
                signature="ok" if self.signature_matches else "mismatch",
            )
            lines.append(summary_line)
            return lines

        def _slice(values: list[RatchetFinding]) -> list[RatchetFinding]:
            if limit is not None and limit > 0:
                return values[:limit]
            return values

        if self.violations:
            lines.append("  Violations:")
            lines.extend([
                (
                    "    "
                    + f"{finding.path} [{finding.severity.value}] "
                    + f"actual={finding.actual} allowed={finding.allowed} delta=+{finding.delta}"
                )
                for finding in _slice(self.violations)
            ])
        else:
            lines.append("  Violations: none")

        if self.improvements:
            lines.append("  Improvements:")
            lines.extend([
                (
                    "    "
                    + f"{finding.path} [{finding.severity.value}] "
                    + f"previous={finding.allowed} current={finding.actual} delta={finding.delta}"
                )
                for finding in _slice(self.improvements)
            ])
        else:
            lines.append("  Improvements: none")

        if not ignore_signature and self.has_signature_mismatch():
            expected_hash = (
                self.expected_signature.get("hash") if self.expected_signature else "<none>"
            )
            actual_hash = self.actual_signature.get("hash") if self.actual_signature else "<none>"
            lines.append(
                "  Engine signature mismatch:" + f" expected={expected_hash} actual={actual_hash}"
            )
        return lines


@dataclass(slots=True)
class RatchetReport:
    """Top-level report containing all evaluated runs."""

    runs: list[RatchetRunReport]

    def has_violations(self) -> bool:
        return any(run.has_violations() for run in self.runs)

    def has_signature_mismatch(self) -> bool:
        return any(run.has_signature_mismatch() for run in self.runs)

    def to_payload(self) -> dict[str, object]:
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
        if self.has_violations():
            return 1
        if not ignore_signature and self.has_signature_mismatch():
            return 1
        return 0


__all__ = [
    "RatchetFinding",
    "RatchetRunReport",
    "RatchetReport",
]
