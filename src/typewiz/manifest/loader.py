# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from typing import Any

from .models import validate_manifest_payload
from .typed import ManifestData


def load_manifest_data(raw: Any) -> ManifestData:
    """Parse manifest payloads using strict validation."""

    return validate_manifest_payload(raw)
