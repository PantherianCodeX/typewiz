# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from typewiz._internal.error_codes import error_code_catalog, error_code_for
from typewiz._internal.exceptions import TypewizError, TypewizTypeError, TypewizValidationError
from typewiz.config import ConfigValidationError
from typewiz.manifest.models import ManifestValidationError


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
            },
        ],
    )
    assert error_code_for(ManifestValidationError(ve)) == "TW300"


def test_error_code_for_unknown_defaults_to_base() -> None:
    class CustomError(RuntimeError):
        pass

    assert error_code_for(CustomError("x")) == "TW000"


def test_error_code_catalog_uniqueness() -> None:
    catalog = error_code_catalog()
    codes = list(catalog.values())
    assert len(set(codes)) == len(codes)
    assert catalog["typewiz._internal.exceptions.TypewizError"] == "TW000"


def test_error_code_documentation_is_in_sync() -> None:
    catalog = error_code_catalog()
    repo_root = Path(__file__).resolve().parents[1]
    doc_path = repo_root / "docs" / "EXCEPTIONS.md"
    content = doc_path.read_text(encoding="utf-8")
    documented_codes = set(re.findall(r"TW\d{3}", content))
    registry_codes = set(catalog.values())
    assert registry_codes == documented_codes
