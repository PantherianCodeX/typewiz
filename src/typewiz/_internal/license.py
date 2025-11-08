# Copyright (c) 2024 PantherianCodeX

"""Runtime helpers for enforcing the Typewiz evaluation license."""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import lru_cache
from typing import Final

from ..model_types import LicenseMode

LICENSE_KEY_ENV: Final[str] = "TYPEWIZ_LICENSE_KEY"
SUPPORT_EMAIL: Final[str] = "pantheriancodex@pm.me"

_notice_emitted = False


@lru_cache(maxsize=1)
def get_license_key() -> str | None:
    """Return the configured license key, if any."""

    key = os.getenv(LICENSE_KEY_ENV)
    if not key:
        return None
    return key.strip() or None


def license_mode() -> LicenseMode:
    """Return the current license mode."""

    return LicenseMode.COMMERCIAL if get_license_key() else LicenseMode.EVALUATION


def has_commercial_license() -> bool:
    """Return True when a license key is present."""

    return license_mode() is LicenseMode.COMMERCIAL


def maybe_emit_evaluation_notice(emitter: Callable[[str], None]) -> None:
    """Emit an evaluation banner once per process when no license key is set."""

    global _notice_emitted  # noqa: PLW0603
    if _notice_emitted:
        return
    if not has_commercial_license():
        message = " ".join([
            "[typewiz] Evaluation mode active. Production use requires a commercial license.",
            f"Set {LICENSE_KEY_ENV}=<key> or contact {SUPPORT_EMAIL}.",
        ])
        emitter(message)
    _notice_emitted = True


def reset_license_notice_state() -> None:
    """Reset cached license state (intended for tests)."""

    global _notice_emitted  # noqa: PLW0603
    _notice_emitted = False
    get_license_key.cache_clear()


__all__ = [
    "LICENSE_KEY_ENV",
    "SUPPORT_EMAIL",
    "get_license_key",
    "has_commercial_license",
    "license_mode",
    "maybe_emit_evaluation_notice",
    "reset_license_notice_state",
]
