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

"""Core data models for s11r2 progress generation."""

from __future__ import annotations

from dataclasses import dataclass

from scripts.docs.s11r2_progress._compat import StrEnum


# ignore JUSTIFIED: StrEnum is Enum+str and pylint overcounts base classes.
class Severity(StrEnum):  # pylint: disable=too-many-ancestors
    """Issue severity levels."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


# ignore JUSTIFIED: StrEnum is Enum+str and pylint overcounts base classes.
class FailOn(StrEnum):  # pylint: disable=too-many-ancestors
    """Failure threshold for the generator."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    NEVER = "NEVER"


@dataclass(frozen=True, slots=True)
class Issue:
    """Single validation or generation issue."""

    severity: Severity
    message: str


@dataclass(frozen=True, slots=True)
class IssueReport:
    """Grouped issues produced during processing."""

    issues: tuple[Issue, ...]

    @property
    def errors(self) -> tuple[Issue, ...]:
        """Return issues marked as errors.

        Returns:
            Error issues.
        """
        return tuple(i for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warnings(self) -> tuple[Issue, ...]:
        """Return issues marked as warnings.

        Returns:
            Warning issues.
        """
        return tuple(i for i in self.issues if i.severity == Severity.WARN)

    @property
    def infos(self) -> tuple[Issue, ...]:
        """Return issues marked as info.

        Returns:
            Info issues.
        """
        return tuple(i for i in self.issues if i.severity == Severity.INFO)

    @property
    def has_errors(self) -> bool:
        """Return True when any errors are present.

        Returns:
            True if any errors exist.
        """
        return any(True for _ in self.errors)

    @property
    def has_warnings(self) -> bool:
        """Return True when any warnings are present.

        Returns:
            True if any warnings exist.
        """
        return any(True for _ in self.warnings)

    @property
    def has_infos(self) -> bool:
        """Return True when any info issues are present.

        Returns:
            True if any info issues exist.
        """
        return any(True for _ in self.infos)

    def should_fail(self, *, fail_on: FailOn) -> bool:
        """Return True when issues meet or exceed the failure threshold.

        Args:
            fail_on: Failure threshold to apply.

        Returns:
            True if the report should cause a non-zero exit.

        Raises:
            ValueError: If fail_on is not supported.
        """
        match fail_on:
            case FailOn.NEVER:
                return False
            case FailOn.ERROR:
                return self.has_errors
            case FailOn.WARN:
                return self.has_errors or self.has_warnings
            case FailOn.INFO:
                return self.has_errors or self.has_warnings or self.has_infos
            case _:
                # ignore JUSTIFIED: Defensive guard for future enum values.
                msg = f"Unsupported fail_on: {fail_on!r}"  # type: ignore[unreachable]
                raise ValueError(msg)


__all__ = ["FailOn", "Issue", "IssueReport", "Severity"]
