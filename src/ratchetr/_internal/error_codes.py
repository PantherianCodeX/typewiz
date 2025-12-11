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

"""Stable error code registry used across ratchetr."""

from __future__ import annotations

from typing import TYPE_CHECKING, NewType

from ratchetr.config import (
    ConfigFieldChoiceError,
    ConfigFieldTypeError,
    ConfigReadError,
    ConfigValidationError,
    DirectoryOverrideValidationError,
    InvalidConfigFileError,
    UndefinedDefaultProfileError,
    UnknownEngineProfileError,
    UnsupportedConfigVersionError,
)
from ratchetr.dashboard import DashboardTypeError
from ratchetr.manifest.models import ManifestValidationError
from ratchetr.manifest.versioning import (
    InvalidManifestRunsError,
    InvalidManifestVersionTypeError,
    UnsupportedManifestVersionError,
)
from ratchetr.readiness.views import ReadinessValidationError

from .exceptions import RatchetrError, RatchetrTypeError, RatchetrValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping

ErrorCode = NewType("ErrorCode", str)

_ERROR_CODES: dict[type[BaseException], ErrorCode] = {
    RatchetrError: ErrorCode("TW000"),
    RatchetrValidationError: ErrorCode("TW100"),
    RatchetrTypeError: ErrorCode("TW101"),
    ConfigValidationError: ErrorCode("TW110"),
    ConfigFieldTypeError: ErrorCode("TW111"),
    ConfigFieldChoiceError: ErrorCode("TW112"),
    UndefinedDefaultProfileError: ErrorCode("TW113"),
    UnknownEngineProfileError: ErrorCode("TW114"),
    UnsupportedConfigVersionError: ErrorCode("TW115"),
    ConfigReadError: ErrorCode("TW116"),
    DirectoryOverrideValidationError: ErrorCode("TW117"),
    InvalidConfigFileError: ErrorCode("TW118"),
    DashboardTypeError: ErrorCode("TW200"),
    ReadinessValidationError: ErrorCode("TW201"),
    ManifestValidationError: ErrorCode("TW300"),
    InvalidManifestRunsError: ErrorCode("TW301"),
    UnsupportedManifestVersionError: ErrorCode("TW302"),
    InvalidManifestVersionTypeError: ErrorCode("TW303"),
}


def error_code_for(exc: BaseException) -> ErrorCode:
    """Return a stable error code for a structured ratchetr exception.

    Args:
        exc: Exception instance raised by ratchetr code paths.

    Returns:
        Error code mapped from the exception's class hierarchy.
    """
    for cls in type(exc).__mro__:
        code = _ERROR_CODES.get(cls)
        if code:
            return code
    return ErrorCode("TW000")


def error_code_catalog() -> Mapping[str, ErrorCode]:
    """Return a stable mapping of fully-qualified exception names to error codes.

    Intended for diagnostics, tests, and documentation generation - avoids
    exposing the private mapping while keeping a single source of truth.

    Returns:
        Mapping of `<module>.<ExceptionName>`strings to error codes.
    """
    result: dict[str, ErrorCode] = {}
    for exc_type, code in _ERROR_CODES.items():
        key = f"{exc_type.__module__}.{exc_type.__name__}"
        result[key] = code
    return result


__all__ = ["ErrorCode", "error_code_catalog", "error_code_for"]
