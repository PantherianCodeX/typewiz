# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Mapping
from typing import NewType

from typewiz._internal.exceptions import TypewizError, TypewizTypeError, TypewizValidationError

from ..config import (
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
from ..dashboard import DashboardTypeError
from ..manifest_models import ManifestValidationError
from ..manifest_versioning import (
    InvalidManifestRunsError,
    InvalidManifestVersionTypeError,
    UnsupportedManifestVersionError,
)
from ..readiness_views import ReadinessValidationError

ErrorCode = NewType("ErrorCode", str)

_ERROR_CODES: dict[type[BaseException], ErrorCode] = {
    TypewizError: ErrorCode("TW000"),
    TypewizValidationError: ErrorCode("TW100"),
    TypewizTypeError: ErrorCode("TW101"),
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
    """Return a stable error code for a structured Typewiz exception."""

    for cls in type(exc).__mro__:
        code = _ERROR_CODES.get(cls)
        if code:
            return code
    return ErrorCode("TW000")


def error_code_catalog() -> Mapping[str, ErrorCode]:
    """Return a stable mapping of fully-qualified exception names to error codes.

    Intended for diagnostics, tests, and documentation generation - avoids
    exposing the private mapping while keeping a single source of truth.
    """

    result: dict[str, ErrorCode] = {}
    for exc_type, code in _ERROR_CODES.items():
        key = f"{exc_type.__module__}.{exc_type.__name__}"
        result[key] = code
    return result


__all__ = ["ErrorCode", "error_code_catalog", "error_code_for"]
