# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""License helpers provided for CLI and packaging layers."""

from __future__ import annotations

from typewiz._internal.license import (  # noqa: F401 - re-exported surface
    LICENSE_KEY_ENV,
    has_commercial_license,
    license_mode,
    maybe_emit_evaluation_notice,
)

__all__ = [
    "LICENSE_KEY_ENV",
    "has_commercial_license",
    "license_mode",
    "maybe_emit_evaluation_notice",
]
