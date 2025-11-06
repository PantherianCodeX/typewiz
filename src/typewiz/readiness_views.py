# Copyright (c) 2024 PantherianCodeX

"""Shared readiness view helpers used by CLI and dashboards."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from .data_validation import (
    coerce_int,
    coerce_mapping,
    coerce_object_list,
    coerce_optional_str,
    coerce_optional_str_list,
    coerce_str,
)
from .model_types import ReadinessStatus
from .summary_types import (
    ReadinessOptionEntry,
    ReadinessOptionsBucket,
    ReadinessStrictEntry,
    SummaryData,
    SummaryTabs,
)


@dataclass(frozen=True, slots=True)
class FolderReadinessRecord:
    path: str
    count: int
    errors: int
    warnings: int

    def to_payload(self) -> dict[str, object]:
        return {
            "path": self.path,
            "count": self.count,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass(frozen=True, slots=True)
class FileReadinessRecord:
    path: str
    diagnostics: int
    errors: int
    warnings: int
    information: int
    notes: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    categories: Mapping[str, int] | None = None
    category_status: Mapping[str, str] | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path,
            "diagnostics": self.diagnostics,
            "errors": self.errors,
            "warnings": self.warnings,
            "information": self.information,
        }
        if self.notes:
            payload["notes"] = list(self.notes)
        if self.recommendations:
            payload["recommendations"] = list(self.recommendations)
        if self.categories:
            payload["categories"] = dict(self.categories)
        if self.category_status:
            # Normalise to camelCase used across summary structures
            payload["categoryStatus"] = dict(self.category_status)
        return payload


class ReadinessValidationError(ValueError):
    """Raised when readiness entries contain invalid data."""


def _build_option_entry(raw: Mapping[str, object]) -> ReadinessOptionEntry:
    entry: ReadinessOptionEntry = {}
    path = raw.get("path")
    if isinstance(path, str):
        entry["path"] = path
    count = raw.get("count")
    if count is not None:
        entry["count"] = coerce_int(count)
    errors = raw.get("errors")
    if errors is not None:
        entry["errors"] = coerce_int(errors)
    warnings = raw.get("warnings")
    if warnings is not None:
        entry["warnings"] = coerce_int(warnings)
    return entry


def _coerce_option_entries(
    mapping_value: Mapping[str, object],
    key: str,
) -> list[ReadinessOptionEntry]:
    entries: list[ReadinessOptionEntry] = []
    for entry in coerce_object_list(mapping_value.get(key)):
        if isinstance(entry, Mapping):
            entry_map = coerce_mapping(cast(Mapping[object, object], entry))
            entries.append(_build_option_entry(cast(Mapping[str, object], entry_map)))
    return entries


def _build_strict_entry(raw: Mapping[str, object]) -> ReadinessStrictEntry:
    entry: ReadinessStrictEntry = {}
    path = raw.get("path")
    if isinstance(path, str):
        entry["path"] = path
    diagnostics = raw.get("diagnostics")
    if diagnostics is not None:
        entry["diagnostics"] = coerce_int(diagnostics)
    errors = raw.get("errors")
    if errors is not None:
        entry["errors"] = coerce_int(errors)
    warnings = raw.get("warnings")
    if warnings is not None:
        entry["warnings"] = coerce_int(warnings)
    information = raw.get("information")
    if information is not None:
        entry["information"] = coerce_int(information)
    notes = coerce_optional_str_list(raw.get("notes"))
    if notes:
        entry["notes"] = notes
    recommendations = coerce_optional_str_list(raw.get("recommendations"))
    if recommendations:
        entry["recommendations"] = recommendations
    categories_raw = raw.get("categories")
    if isinstance(categories_raw, Mapping):
        categories_map = coerce_mapping(cast(Mapping[object, object], categories_raw))
        entry["categories"] = {key: coerce_int(value) for key, value in categories_map.items()}
    category_status_raw = raw.get("categoryStatus")
    if isinstance(category_status_raw, Mapping):
        status_map = coerce_mapping(cast(Mapping[object, object], category_status_raw))
        entry["categoryStatus"] = {key: coerce_str(value) for key, value in status_map.items()}
    return entry


def _coerce_options_bucket(value: object) -> ReadinessOptionsBucket:
    bucket: ReadinessOptionsBucket = {}
    if not isinstance(value, Mapping):
        return bucket
    mapping_value = coerce_mapping(cast(Mapping[object, object], value))
    for status in ReadinessStatus:
        entries = _coerce_option_entries(mapping_value, status.value)
        if not entries:
            continue
        bucket[status.value] = entries
    threshold_val = mapping_value.get("threshold")
    if isinstance(threshold_val, int):
        bucket["threshold"] = threshold_val
    return bucket


def _coerce_options_map(raw: object) -> dict[str, ReadinessOptionsBucket]:
    if not isinstance(raw, Mapping):
        return {}
    mapping_value = cast(Mapping[object, object], raw)
    return {str(key): _coerce_options_bucket(value) for key, value in mapping_value.items()}


def _coerce_strict_map(raw: object) -> dict[str, list[ReadinessStrictEntry]]:
    if not isinstance(raw, Mapping):
        return {}
    mapping_value = cast(Mapping[object, object], raw)
    return {str(key): _coerce_strict_entries(value) for key, value in mapping_value.items()}


def _coerce_strict_entries(value: object) -> list[ReadinessStrictEntry]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return []
    entries: list[ReadinessStrictEntry] = []
    for entry in cast(Sequence[object], value):
        if isinstance(entry, Mapping):
            entry_map = coerce_mapping(cast(Mapping[object, object], entry))
            entries.append(_build_strict_entry(cast(Mapping[str, object], entry_map)))
    return entries


def _normalise_folder_entry(entry: ReadinessOptionEntry) -> FolderReadinessRecord:
    path = coerce_str(entry.get("path"), "<unknown>")
    count = coerce_int(entry.get("count"))
    errors = coerce_int(entry.get("errors"))
    warnings = coerce_int(entry.get("warnings"))
    return FolderReadinessRecord(path=path, count=count, errors=errors, warnings=warnings)


def _normalise_file_entry(entry: ReadinessStrictEntry) -> FileReadinessRecord:
    path = coerce_str(entry.get("path"), "<unknown>")
    diagnostics = coerce_int(entry.get("diagnostics"))
    if diagnostics < 0:
        message = "diagnostics must be non-negative"
        raise ValueError(message)
    errors = coerce_int(entry.get("errors"))
    if errors < 0:
        message = "errors must be non-negative"
        raise ValueError(message)
    warnings = coerce_int(entry.get("warnings"))
    if warnings < 0:
        message = "warnings must be non-negative"
        raise ValueError(message)
    information = coerce_int(entry.get("information"))
    if information < 0:
        message = "information must be non-negative"
        raise ValueError(message)
    notes_items = coerce_optional_str_list(entry.get("notes"))
    recommendations_items = coerce_optional_str_list(entry.get("recommendations"))
    categories_map = coerce_mapping(entry.get("categories"))
    categories: Mapping[str, int] | None = None
    if categories_map:
        categories = {key: coerce_int(value) for key, value in categories_map.items()}
    status_map = coerce_mapping(entry.get("categoryStatus"))
    category_status: Mapping[str, str] | None = None
    if status_map:
        category_status = {
            key: coerce_optional_str(value) or "unknown" for key, value in status_map.items()
        }
    return FileReadinessRecord(
        path=path,
        diagnostics=diagnostics,
        errors=errors,
        warnings=warnings,
        information=information,
        notes=tuple(notes_items) if notes_items else (),
        recommendations=tuple(recommendations_items) if recommendations_items else (),
        categories=categories,
        category_status=category_status,
    )


def _extract_folder_entries(
    bucket: ReadinessOptionsBucket,
    status: str,
) -> list[ReadinessOptionEntry]:
    entries = bucket.get(status)
    if isinstance(entries, list):
        return cast(list[ReadinessOptionEntry], entries)
    return []


def _extract_file_entries(
    strict_map: Mapping[str, Sequence[ReadinessStrictEntry]],
    status: str,
) -> list[ReadinessStrictEntry]:
    entries = strict_map.get(status)
    if isinstance(entries, list):
        return entries
    return []


def _normalise_status_filters(statuses: Sequence[str] | None) -> list[str]:
    if statuses is None:
        return [ReadinessStatus.BLOCKED.value]
    result: list[str] = []
    for status in statuses:
        try:
            parsed = ReadinessStatus.from_str(status)
        except ValueError:
            continue
        if parsed.value not in result:
            result.append(parsed.value)
    return result or [ReadinessStatus.BLOCKED.value]


def _folder_payload_for_status(
    options_tab: Mapping[str, ReadinessOptionsBucket],
    status: str,
    limit: int,
) -> list[dict[str, object]]:
    # Prefer unknownChecks, then optionalChecks, then unusedSymbols, then general
    category_order = ("unknownChecks", "optionalChecks", "unusedSymbols", "general")
    entries: list[ReadinessOptionEntry] = []
    for category in category_order:
        bucket = options_tab.get(category, {})
        entries = _extract_folder_entries(bucket, status)
        if entries:
            break
    records: list[FolderReadinessRecord] = []
    for option_entry in entries:
        try:
            records.append(_normalise_folder_entry(option_entry))
        except ValueError as exc:
            raise ReadinessValidationError(str(exc)) from exc
    if limit > 0:
        records = records[:limit]
    return [record.to_payload() for record in records]


def _file_payload_for_status(
    strict_map: Mapping[str, list[ReadinessStrictEntry]],
    status: str,
    limit: int,
) -> list[dict[str, object]]:
    entries = _extract_file_entries(strict_map, status)
    records: list[FileReadinessRecord] = []
    for strict_entry in entries:
        try:
            records.append(_normalise_file_entry(strict_entry))
        except ValueError as exc:
            raise ReadinessValidationError(str(exc)) from exc
    if limit > 0:
        records = records[:limit]
    return [record.to_payload() for record in records]


def collect_readiness_view(
    summary: SummaryData,
    *,
    level: str,
    statuses: Sequence[str] | None,
    limit: int,
) -> dict[str, list[dict[str, object]]]:
    tabs: SummaryTabs = summary["tabs"]
    readiness_tab = tabs.get("readiness") or {}
    options_tab = _coerce_options_map(readiness_tab.get("options"))
    strict_map = _coerce_strict_map(readiness_tab.get("strict"))

    statuses_normalised = _normalise_status_filters(statuses)
    result: dict[str, list[dict[str, object]]] = {}
    for status in statuses_normalised:
        if level == "folder":
            result[status] = _folder_payload_for_status(options_tab, status, limit)
        else:
            result[status] = _file_payload_for_status(strict_map, status, limit)
    return result
