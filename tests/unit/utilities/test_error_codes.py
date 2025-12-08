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

"""Unit tests for Utilities Error Codes."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from ratchetr._internal.error_codes import error_code_catalog, error_code_for
from ratchetr._internal.exceptions import RatchetrError, RatchetrTypeError, RatchetrValidationError
from ratchetr.config import ConfigValidationError
from ratchetr.manifest.models import ManifestValidationError

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_error_code_for_known_hierarchy() -> None:
    assert error_code_for(RatchetrError("x")) == "TW000"
    assert error_code_for(RatchetrValidationError("x")) == "TW100"
    assert error_code_for(RatchetrTypeError("x")) == "TW101"
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
    assert catalog["ratchetr._internal.exceptions.RatchetrError"] == "TW000"


def test_error_code_documentation_is_in_sync() -> None:
    catalog = error_code_catalog()
    doc_path = REPO_ROOT / "docs" / "EXCEPTIONS.md"
    content = doc_path.read_text(encoding="utf-8")
    documented_codes = set(re.findall(r"TW\d{3}", content))
    registry_codes = set(catalog.values())
    assert registry_codes == documented_codes
