# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Load and validate manifest data from raw input.

This module provides utilities for loading manifest data from arbitrary
sources (typically JSON files) and validating them against the manifest schema.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models import validate_manifest_payload

if TYPE_CHECKING:
    from .typed import ManifestData


def load_manifest_data(raw: Any) -> ManifestData:
    """Parse manifest payloads using strict validation.

    Args:
        raw: Raw manifest data from any source (typically parsed JSON).

    Returns:
        Validated ManifestData TypedDict.
    """
    return validate_manifest_payload(raw)
