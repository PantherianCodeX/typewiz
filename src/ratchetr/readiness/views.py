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

"""Shared readiness view helpers used by CLI and dashboards."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from ratchetr.compat import TypedDict
from ratchetr.config.validation import (
    coerce_int,
    coerce_mapping,
    coerce_object_list,
    coerce_optional_str_list,
    coerce_str,
)
from ratchetr.core.categories import CATEGORY_DISPLAY_ORDER, coerce_category_key
from ratchetr.core.model_types import ReadinessLevel, ReadinessStatus, SeverityLevel
from ratchetr.core.type_aliases import CategoryKey, CategoryName
from ratchetr.readiness.compute import DEFAULT_CLOSE_THRESHOLD, ReadinessOptions

if TYPE_CHECKING:
    from ratchetr.core.summary_types import (
        ReadinessOptionEntry,
        ReadinessStrictEntry,
        SummaryData,
        SummaryTabs,
    )


@dataclass(frozen=True, slots=True)
class FolderReadinessRecord:
    """Record representing folder-level readiness metrics.

    Attributes:
        path (str): The folder path.
        count (int): Total diagnostic count.
        errors (int): Number of error-level diagnostics.
        warnings (int): Number of warning-level diagnostics.
        information (int): Number of information-level diagnostics.
    """

    path: str
    count: int
    errors: int
    warnings: int
    information: int

    def to_payload(self) -> FolderReadinessPayload:
        """Convert to a serializable payload.

        Returns:
            FolderReadinessPayload: A dictionary representation of the folder readiness.
        """
        return FolderReadinessPayload(
            path=self.path,
            count=self.count,
            errors=self.errors,
            warnings=self.warnings,
            information=self.information,
        )


class FolderReadinessPayload(TypedDict):
    """Folder-level readiness data for serialization.

    Attributes:
        path (str): The folder path.
        count (int): Total diagnostic count.
        errors (int): Number of error-level diagnostics.
        warnings (int): Number of warning-level diagnostics.
        information (int): Number of information-level diagnostics.
    """

    path: str
    count: int
    errors: int
    warnings: int
    information: int


class FileReadinessPayloadBase(TypedDict):
    """Base file-level readiness data.

    Attributes:
        path (str): The file path.
        diagnostics (int): Total diagnostic count.
        errors (int): Number of error-level diagnostics.
        warnings (int): Number of warning-level diagnostics.
        information (int): Number of information-level diagnostics.
    """

    path: str
    diagnostics: int
    errors: int
    warnings: int
    information: int


class FileReadinessPayload(FileReadinessPayloadBase, total=False):
    """Complete file-level readiness data with optional fields.

    Attributes:
        notes (list[str]): Optional explanatory notes.
        recommendations (list[str]): Optional improvement recommendations.
        categories (dict[CategoryName, int]): Optional category-specific diagnostic counts.
        categoryStatus (dict[CategoryName, ReadinessStatus]): Optional per-category readiness status.
    """

    notes: list[str]
    recommendations: list[str]
    categories: dict[CategoryName, int]
    # ignore JUSTIFIED: readiness summary payload uses camelCase keys to align with
    # external JSON schema
    categoryStatus: dict[CategoryName, ReadinessStatus]  # noqa: FIX002, TD003  # TODO@PantherianCodeX: Restrict N815 ignores to JSON boundary after implementing schema validation


@dataclass(frozen=True, slots=True)
# ignore JUSTIFIED: intentional - readiness record carries full metrics snapshot
class FileReadinessRecord:  # pylint: disable=too-many-instance-attributes
    """Record representing file-level readiness metrics.

    Attributes:
        path (str): The file path.
        diagnostics (int): Total diagnostic count.
        errors (int): Number of error-level diagnostics.
        warnings (int): Number of warning-level diagnostics.
        information (int): Number of information-level diagnostics.
        notes (tuple[str, ...]): Explanatory notes. Defaults to empty tuple.
        recommendations (tuple[str, ...]): Improvement recommendations. Defaults to empty tuple.
        categories (Mapping[CategoryName, int] | None): Category-specific diagnostic counts. Defaults to None.
        category_status (Mapping[CategoryName, ReadinessStatus] | None): Per-category readiness status. Defaults to None
    """

    path: str
    diagnostics: int
    errors: int
    warnings: int
    information: int
    notes: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    categories: Mapping[CategoryName, int] | None = None
    category_status: Mapping[CategoryName, ReadinessStatus] | None = None

    def to_payload(self) -> FileReadinessPayload:
        """Convert to a serializable payload.

        Returns:
            FileReadinessPayload: A dictionary representation of the file readiness.
        """
        payload: FileReadinessPayload = {
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
            # normalize to camelCase used across summary structures
            payload["categoryStatus"] = dict(self.category_status)
        return payload


class ReadinessValidationError(ValueError):
    """Raised when readiness entries contain invalid data."""


def _build_option_entry(raw: Mapping[str, object]) -> ReadinessOptionEntry:
    """Build a ReadinessOptionEntry from raw data.

    Args:
        raw (Mapping[str, object]): Raw entry data.

    Returns:
        ReadinessOptionEntry: A validated option entry.
    """
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


def _coerce_status(value: object) -> ReadinessStatus:
    """Coerce a value to a ReadinessStatus.

    Args:
        value (object): The value to coerce.

    Returns:
        ReadinessStatus: The coerced status, defaulting to BLOCKED if invalid.
    """
    if isinstance(value, ReadinessStatus):
        return value
    if isinstance(value, str):
        try:
            return ReadinessStatus.from_str(value)
        except ValueError:
            return ReadinessStatus.BLOCKED
    return ReadinessStatus.BLOCKED


def _coerce_option_entries(value: object) -> list[ReadinessOptionEntry]:
    """Coerce a value to a list of ReadinessOptionEntry.

    Args:
        value (object): The value to coerce.

    Returns:
        list[ReadinessOptionEntry]: A list of validated option entries.
    """
    entries: list[ReadinessOptionEntry] = []
    for entry in coerce_object_list(value):
        if isinstance(entry, Mapping):
            entry_map = coerce_mapping(cast("Mapping[object, object]", entry))
            entries.append(_build_option_entry(cast("Mapping[str, object]", entry_map)))
    return entries


# ignore JUSTIFIED: strict entry builder performs tightly coupled field coercions;
# splitting further would obscure the data-mapping logic
def _build_strict_entry(raw: Mapping[str, object]) -> ReadinessStrictEntry:  # noqa: C901
    """Build a ReadinessStrictEntry from raw data.

    Args:
        raw (Mapping[str, object]): Raw entry data.

    Returns:
        ReadinessStrictEntry: A validated strict entry.
    """
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
        categories_map = coerce_mapping(cast("Mapping[object, object]", categories_raw))
        entry["categories"] = {CategoryName(str(key)): coerce_int(value) for key, value in categories_map.items()}
    category_status_raw = raw.get("categoryStatus")
    if isinstance(category_status_raw, Mapping):
        status_map: dict[CategoryName, ReadinessStatus] = {
            CategoryName(str(key)): _coerce_status(value)
            for key, value in cast("Mapping[object, object]", category_status_raw).items()
        }
        if status_map:
            entry["categoryStatus"] = status_map
    return entry


def _coerce_options_bucket(value: object) -> ReadinessOptions:
    """Coerce a value to a ReadinessOptions bucket.

    Args:
        value (object): The value to coerce.

    Returns:
        ReadinessOptions: A validated options bucket.
    """
    if not isinstance(value, Mapping):
        return ReadinessOptions(threshold=DEFAULT_CLOSE_THRESHOLD)
    mapping_value = coerce_mapping(cast("Mapping[object, object]", value))
    threshold_val = mapping_value.get("threshold")
    threshold = threshold_val if isinstance(threshold_val, int) else DEFAULT_CLOSE_THRESHOLD
    bucket = ReadinessOptions(threshold=threshold)
    bucket_section = mapping_value.get("buckets")
    if isinstance(bucket_section, Mapping):
        buckets_map = coerce_mapping(cast("Mapping[object, object]", bucket_section))
        for key, entries_raw in buckets_map.items():
            status = _coerce_status(key)
            entries = _coerce_option_entries(entries_raw)
            if not entries:
                continue
            for entry in entries:
                bucket.add_entry(status, entry)
    return bucket


def _coerce_options_map(raw: object) -> dict[CategoryKey, ReadinessOptions]:
    """Coerce raw data to an options map.

    Args:
        raw (object): The raw data to coerce.

    Returns:
        dict[CategoryKey, ReadinessOptions]: A mapping of categories to options.
    """
    if not isinstance(raw, Mapping):
        return {}
    mapping_value = cast("Mapping[object, object]", raw)
    result: dict[CategoryKey, ReadinessOptions] = {}
    for key, value in mapping_value.items():
        category_key = coerce_category_key(key)
        if category_key is None:
            continue
        result[category_key] = _coerce_options_bucket(value)
    return result


def _coerce_strict_map(raw: object) -> dict[ReadinessStatus, list[ReadinessStrictEntry]]:
    """Coerce raw data to a strict entries map.

    Args:
        raw (object): The raw data to coerce.

    Returns:
        dict[ReadinessStatus, list[ReadinessStrictEntry]]: A mapping of status to strict entries.
    """
    if not isinstance(raw, Mapping):
        return {}
    mapping_value = cast("Mapping[object, object]", raw)
    result: dict[ReadinessStatus, list[ReadinessStrictEntry]] = {}
    for key, value in mapping_value.items():
        status = _coerce_status(key)
        result[status] = _coerce_strict_entries(value)
    return result


def _coerce_strict_entries(value: object) -> list[ReadinessStrictEntry]:
    """Coerce a value to a list of ReadinessStrictEntry.

    Args:
        value (object): The value to coerce.

    Returns:
        list[ReadinessStrictEntry]: A list of validated strict entries.
    """
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return []
    entries: list[ReadinessStrictEntry] = []
    for entry in cast("Sequence[object]", value):
        if isinstance(entry, Mapping):
            entry_map = coerce_mapping(cast("Mapping[object, object]", entry))
            entries.append(_build_strict_entry(cast("Mapping[str, object]", entry_map)))
    return entries


def _normalize_folder_entry(entry: ReadinessOptionEntry) -> FolderReadinessRecord:
    """Normalize an option entry to a folder readiness record.

    Args:
        entry (ReadinessOptionEntry): The option entry to normalize.

    Returns:
        FolderReadinessRecord: A normalized folder readiness record.
    """
    path = coerce_str(entry.get("path"), "<unknown>")
    count = coerce_int(entry.get("count"))
    errors = coerce_int(entry.get("errors"))
    warnings = coerce_int(entry.get("warnings"))
    information = max(0, count - errors - warnings)
    return FolderReadinessRecord(
        path=path,
        count=count,
        errors=errors,
        warnings=warnings,
        information=information,
    )


def _normalize_file_entry(entry: ReadinessStrictEntry) -> FileReadinessRecord:
    """Normalize a strict entry to a file readiness record.

    Args:
        entry (ReadinessStrictEntry): The strict entry to normalize.

    Returns:
        FileReadinessRecord: A normalized file readiness record.

    Raises:
        ValueError: If any count field is negative.
    """
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
    categories: Mapping[CategoryName, int] | None = None
    if categories_map:
        categories = {CategoryName(str(key)): coerce_int(value) for key, value in categories_map.items()}
    status_source = entry.get("categoryStatus")
    category_status: Mapping[CategoryName, ReadinessStatus] | None = None
    if isinstance(status_source, Mapping) and status_source:
        converted: dict[CategoryName, ReadinessStatus] = {
            CategoryName(str(key)): _coerce_status(value)
            for key, value in cast("Mapping[str, object]", status_source).items()
        }
        category_status = converted or None
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


def _normalize_severity_filters(
    severities: Sequence[SeverityLevel] | None,
) -> tuple[SeverityLevel, ...]:
    """Normalize and deduplicate severity filters.

    Args:
        severities (Sequence[SeverityLevel] | None): The severity filters to normalize.

    Returns:
        tuple[SeverityLevel, ...]: A deduplicated tuple of severity levels.
    """
    if not severities:
        return ()
    ordered: list[SeverityLevel] = []
    for severity in severities:
        if severity not in ordered:
            ordered.append(severity)
    return tuple(ordered)


def _folder_matches_severity(
    record: FolderReadinessRecord,
    severities: Sequence[SeverityLevel],
) -> bool:
    """Check if a folder record matches any of the given severities.

    Args:
        record (FolderReadinessRecord): The folder record to check.
        severities (Sequence[SeverityLevel]): The severity levels to match against.

    Returns:
        bool: True if the record has diagnostics matching any of the severities.
    """
    if not severities:
        return True
    for severity in severities:
        if severity is SeverityLevel.ERROR and record.errors > 0:
            return True
        if severity is SeverityLevel.WARNING and record.warnings > 0:
            return True
        if severity is SeverityLevel.INFORMATION and record.information > 0:
            return True
    return False


def _file_matches_severity(
    record: FileReadinessRecord,
    severities: Sequence[SeverityLevel],
) -> bool:
    """Check if a file record matches any of the given severities.

    Args:
        record (FileReadinessRecord): The file record to check.
        severities (Sequence[SeverityLevel]): The severity levels to match against.

    Returns:
        bool: True if the record has diagnostics matching any of the severities.
    """
    if not severities:
        return True
    for severity in severities:
        if severity is SeverityLevel.ERROR and record.errors > 0:
            return True
        if severity is SeverityLevel.WARNING and record.warnings > 0:
            return True
        if severity is SeverityLevel.INFORMATION and record.information > 0:
            return True
    return False


def _extract_file_entries(
    strict_map: Mapping[ReadinessStatus, Sequence[ReadinessStrictEntry]],
    status: ReadinessStatus,
) -> list[ReadinessStrictEntry]:
    """Extract file entries for a specific status from the strict map.

    Args:
        strict_map (Mapping[ReadinessStatus, Sequence[ReadinessStrictEntry]]): The map of strict entries.
        status (ReadinessStatus): The status to extract entries for.

    Returns:
        list[ReadinessStrictEntry]: The entries matching the status.
    """
    entries = strict_map.get(status)
    if isinstance(entries, list):
        return entries
    return []


def _normalize_status_filters(
    statuses: Sequence[ReadinessStatus] | None,
) -> list[ReadinessStatus]:
    """Normalize and deduplicate status filters.

    Args:
        statuses (Sequence[ReadinessStatus] | None): The status filters to normalize.

    Returns:
        list[ReadinessStatus]: A deduplicated list, defaulting to [BLOCKED] if None or empty.
    """
    if statuses is None:
        return [ReadinessStatus.BLOCKED]
    normalized: list[ReadinessStatus] = []
    for status in statuses:
        if status not in normalized:
            normalized.append(status)
    return normalized or [ReadinessStatus.BLOCKED]


def _folder_payload_for_status(
    options_tab: Mapping[CategoryKey, ReadinessOptions],
    status: ReadinessStatus,
    limit: int,
    severities: Sequence[SeverityLevel],
) -> list[FolderReadinessPayload]:
    """Generate folder payloads for a specific readiness status.

    Args:
        options_tab (Mapping[CategoryKey, ReadinessOptions]): The options data by category.
        status (ReadinessStatus): The status to filter for.
        limit (int): Maximum number of entries to return (0 for no limit).
        severities (Sequence[SeverityLevel]): Severity filters to apply.

    Returns:
        list[FolderReadinessPayload]: Filtered and limited folder payloads.

    Raises:
        ReadinessValidationError: If entry normalization fails.
    """
    entries: list[ReadinessOptionEntry] = []
    for category in CATEGORY_DISPLAY_ORDER:
        bucket = options_tab.get(category)
        if bucket is None:
            continue
        bucket_entries = bucket.buckets.get(status, ())
        if not bucket_entries:
            continue
        entries = list(bucket_entries)
        if entries:
            break
    records: list[FolderReadinessRecord] = []
    for option_entry in entries:
        try:
            records.append(_normalize_folder_entry(option_entry))
        # ignore JUSTIFIED: preserve original ValueError context when wrapping in
        # ReadinessValidationError
        except ValueError as exc:  # noqa: PERF203
            raise ReadinessValidationError(str(exc)) from exc
    records = [record for record in records if _folder_matches_severity(record, severities)]
    if limit > 0:
        records = records[:limit]
    return [record.to_payload() for record in records]


def _file_payload_for_status(
    strict_map: Mapping[ReadinessStatus, list[ReadinessStrictEntry]],
    status: ReadinessStatus,
    limit: int,
    severities: Sequence[SeverityLevel],
) -> list[FileReadinessPayload]:
    """Generate file payloads for a specific readiness status.

    Args:
        strict_map (Mapping[ReadinessStatus, list[ReadinessStrictEntry]]): The strict entries by status.
        status (ReadinessStatus): The status to filter for.
        limit (int): Maximum number of entries to return (0 for no limit).
        severities (Sequence[SeverityLevel]): Severity filters to apply.

    Returns:
        list[FileReadinessPayload]: Filtered and limited file payloads.

    Raises:
        ReadinessValidationError: If entry normalization fails.
    """
    entries = _extract_file_entries(strict_map, status)
    records: list[FileReadinessRecord] = []
    for strict_entry in entries:
        try:
            records.append(_normalize_file_entry(strict_entry))
        # ignore JUSTIFIED: preserve original ValueError context when wrapping in
        # ReadinessValidationError
        except ValueError as exc:  # noqa: PERF203
            raise ReadinessValidationError(str(exc)) from exc
    records = [record for record in records if _file_matches_severity(record, severities)]
    if limit > 0:
        records = records[:limit]
    return [record.to_payload() for record in records]


FolderReadinessView = dict[ReadinessStatus, list[FolderReadinessPayload]]
FileReadinessView = dict[ReadinessStatus, list[FileReadinessPayload]]
ReadinessViewResult = FolderReadinessView | FileReadinessView


def collect_readiness_view(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
    severities: Sequence[SeverityLevel] | None = None,
) -> ReadinessViewResult:
    """Collect readiness view data from a summary.

    Args:
        summary (SummaryData): The complete summary data containing readiness information.
        level (ReadinessLevel): Whether to return FOLDER or FILE level data.
        statuses (Sequence[ReadinessStatus] | None): Status filters to apply (defaults to [BLOCKED]).
        limit (int): Maximum number of entries per status (0 for no limit).
        severities (Sequence[SeverityLevel] | None, optional): Severity filters to apply. Defaults to None.

    Returns:
        ReadinessViewResult: A view mapping statuses to either folder or file payloads.
    """
    tabs: SummaryTabs = summary["tabs"]
    readiness_tab = tabs.get("readiness") or {}
    options_tab = _coerce_options_map(readiness_tab.get("options"))
    strict_map = _coerce_strict_map(readiness_tab.get("strict"))

    statuses_normalized = _normalize_status_filters(statuses)
    severity_filter = _normalize_severity_filters(severities)
    if level is ReadinessLevel.FOLDER:
        view: FolderReadinessView = {}
        for status in statuses_normalized:
            view[status] = _folder_payload_for_status(
                options_tab,
                status,
                limit,
                severity_filter,
            )
        return view
    file_view: FileReadinessView = {}
    for status in statuses_normalized:
        file_view[status] = _file_payload_for_status(
            strict_map,
            status,
            limit,
            severity_filter,
        )
    return file_view
