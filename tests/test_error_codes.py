from __future__ import annotations

from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from typewiz.config import ConfigValidationError
from typewiz.error_codes import error_code_for
from typewiz.exceptions import TypewizError, TypewizTypeError, TypewizValidationError
from typewiz.manifest_models import ManifestValidationError


def test_error_code_for_known_hierarchy() -> None:
    assert error_code_for(TypewizError("x")) == "TW000"
    assert error_code_for(TypewizValidationError("x")) == "TW100"
    assert error_code_for(TypewizTypeError("x")) == "TW101"
    assert error_code_for(ConfigValidationError("x")) == "TW110"
    custom = PydanticCustomError("manifest.runs.type", "runs must be a list of run payloads", {})
    ve = ValidationError.from_exception_data(
        "ManifestModel",
        [
            {
                "type": custom,
                "loc": ("runs",),
                "input": {},
            }
        ],
    )
    assert error_code_for(ManifestValidationError(ve)) == "TW300"


def test_error_code_for_unknown_defaults_to_base() -> None:
    class CustomError(RuntimeError):
        pass

    assert error_code_for(CustomError("x")) == "TW000"
