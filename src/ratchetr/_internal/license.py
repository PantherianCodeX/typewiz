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

"""Runtime helpers for enforcing the ratchetr evaluation license."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Final

from ratchetr.core.model_types import LicenseMode

if TYPE_CHECKING:
    from collections.abc import Callable


LICENSE_KEY_ENV: Final[str] = "RATCHETR_LICENSE_KEY"
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
            "[ratchetr] Evaluation mode active. Production use requires a commercial license.",
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
