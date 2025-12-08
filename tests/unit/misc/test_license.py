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

"""Unit tests for Misc License."""

from __future__ import annotations

import pytest

from ratchetr._internal import license as license_mod
from ratchetr.core.model_types import LicenseMode

pytestmark = pytest.mark.unit


def _reset_license(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(license_mod.LICENSE_KEY_ENV, raising=False)
    license_mod.reset_license_notice_state()


def test_license_mode_defaults_to_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_license(monkeypatch)

    assert license_mod.license_mode() is LicenseMode.EVALUATION
    assert not license_mod.has_commercial_license()


def test_license_mode_detects_commercial_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_license(monkeypatch)
    monkeypatch.setenv(license_mod.LICENSE_KEY_ENV, "demo-key")

    assert license_mod.license_mode() is LicenseMode.COMMERCIAL
    assert license_mod.has_commercial_license()
