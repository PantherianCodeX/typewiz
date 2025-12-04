# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Misc License."""

from __future__ import annotations

import pytest
from pytest import MonkeyPatch

from typewiz._internal import license as license_mod
from typewiz.core.model_types import LicenseMode

pytestmark = pytest.mark.unit


def _reset_license(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv(license_mod.LICENSE_KEY_ENV, raising=False)
    license_mod.reset_license_notice_state()


def test_license_mode_defaults_to_evaluation(monkeypatch: MonkeyPatch) -> None:
    _reset_license(monkeypatch)

    assert license_mod.license_mode() is LicenseMode.EVALUATION
    assert not license_mod.has_commercial_license()


def test_license_mode_detects_commercial_key(monkeypatch: MonkeyPatch) -> None:
    _reset_license(monkeypatch)
    monkeypatch.setenv(license_mod.LICENSE_KEY_ENV, "demo-key")

    assert license_mod.license_mode() is LicenseMode.COMMERCIAL
    assert license_mod.has_commercial_license()
