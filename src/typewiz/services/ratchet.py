from __future__ import annotations

from pathlib import Path
from typing import Any

from typewiz.manifest.typed import ManifestData
from typewiz.ratchet import (
    apply_auto_update as _apply_auto_update,
)
from typewiz.ratchet import (
    build_ratchet_from_manifest as _build_ratchet_from_manifest,
)
from typewiz.ratchet import (
    compare_manifest_to_ratchet as _compare_manifest_to_ratchet,
)
from typewiz.ratchet import (
    load_ratchet as _load_ratchet,
)
from typewiz.ratchet import (
    refresh_signatures as _refresh_signatures,
)
from typewiz.ratchet import (
    write_ratchet as _write_ratchet,
)
from typewiz.ratchet.io import current_timestamp as _current_timestamp
from typewiz.ratchet.io import load_manifest as _load_manifest
from typewiz.ratchet.models import RatchetModel
from typewiz.ratchet.summary import RatchetReport


def load_manifest(path: Path) -> ManifestData:
    return _load_manifest(path)


def load_ratchet(path: Path) -> RatchetModel:
    return _load_ratchet(path)


def write_ratchet(path: Path, model: RatchetModel) -> None:
    _write_ratchet(path, model)


def build_ratchet_from_manifest(**kwargs: Any) -> RatchetModel:
    return _build_ratchet_from_manifest(**kwargs)


def compare_manifest_to_ratchet(**kwargs: Any) -> RatchetReport:
    return _compare_manifest_to_ratchet(**kwargs)


def apply_auto_update(**kwargs: Any) -> RatchetModel:
    return _apply_auto_update(**kwargs)


def refresh_signatures(**kwargs: Any) -> RatchetModel:
    return _refresh_signatures(**kwargs)


def current_timestamp() -> str:
    return _current_timestamp()


__all__ = [
    "apply_auto_update",
    "build_ratchet_from_manifest",
    "compare_manifest_to_ratchet",
    "load_manifest",
    "load_ratchet",
    "write_ratchet",
    "refresh_signatures",
    "current_timestamp",
    "RatchetReport",
]
