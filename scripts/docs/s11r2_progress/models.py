"""Core data models for s11r2 progress generation."""

from __future__ import annotations

from dataclasses import dataclass

from scripts.docs.s11r2_progress._compat import StrEnum


class Severity(StrEnum):
    """Issue severity levels."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


class FailOn(StrEnum):
    """Failure threshold for the generator."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    NEVER = "NEVER"


@dataclass(frozen=True, slots=True)
class Issue:
    severity: Severity
    message: str


@dataclass(frozen=True, slots=True)
class IssueReport:
    issues: tuple[Issue, ...]

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warnings(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == Severity.WARN)

    @property
    def infos(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == Severity.INFO)

    @property
    def has_errors(self) -> bool:
        return any(True for _ in self.errors)

    @property
    def has_warnings(self) -> bool:
        return any(True for _ in self.warnings)

    @property
    def has_infos(self) -> bool:
        return any(True for _ in self.infos)

    def should_fail(self, *, fail_on: FailOn) -> bool:
        if fail_on == FailOn.NEVER:
            return False
        if fail_on == FailOn.ERROR:
            return self.has_errors
        if fail_on == FailOn.WARN:
            return self.has_errors or self.has_warnings
        if fail_on == FailOn.INFO:
            return self.has_errors or self.has_warnings or self.has_infos
        raise ValueError(f"Unsupported fail_on: {fail_on!r}")


__all__ = ["FailOn", "Issue", "IssueReport", "Severity"]
