from __future__ import annotations

from collections.abc import Mapping

from .config import (
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
from .dashboard import DashboardTypeError
from .exceptions import TypewizError, TypewizTypeError, TypewizValidationError
from .manifest_models import ManifestValidationError
from .manifest_versioning import (
    InvalidManifestRunsError,
    InvalidManifestVersionTypeError,
    UnsupportedManifestVersionError,
)
from .readiness_views import ReadinessValidationError

ErrorCode = str

_ERROR_CODES: dict[type[BaseException], ErrorCode] = {
    TypewizError: "TW000",
    TypewizValidationError: "TW100",
    TypewizTypeError: "TW101",
    ConfigValidationError: "TW110",
    ConfigFieldTypeError: "TW111",
    ConfigFieldChoiceError: "TW112",
    UndefinedDefaultProfileError: "TW113",
    UnknownEngineProfileError: "TW114",
    UnsupportedConfigVersionError: "TW115",
    ConfigReadError: "TW116",
    DirectoryOverrideValidationError: "TW117",
    InvalidConfigFileError: "TW118",
    DashboardTypeError: "TW200",
    ReadinessValidationError: "TW201",
    ManifestValidationError: "TW300",
    InvalidManifestRunsError: "TW301",
    UnsupportedManifestVersionError: "TW302",
    InvalidManifestVersionTypeError: "TW303",
}


def error_code_for(exc: BaseException) -> ErrorCode:
    """Return a stable error code for a structured Typewiz exception."""

    for cls in type(exc).__mro__:
        code = _ERROR_CODES.get(cls)
        if code:
            return code
    return "TW000"


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
