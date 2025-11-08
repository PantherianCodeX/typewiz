# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import hypothesis.strategies as st
import pytest
from hypothesis import HealthCheck, assume, given, settings

from typewiz._internal.utils import consume
from typewiz.manifest_models import ManifestValidationError, validate_manifest_payload
from typewiz.manifest_versioning import CURRENT_MANIFEST_VERSION


def _run_payloads() -> st.SearchStrategy[dict[str, Any]]:
    severity = st.integers(min_value=0, max_value=10)
    summary: st.SearchStrategy[dict[str, Any]] = st.fixed_dictionaries(
        {
            "errors": severity,
            "warnings": severity,
            "information": severity,
            "total": st.integers(min_value=0, max_value=30),
        },
    )
    file_entry: st.SearchStrategy[dict[str, Any]] = st.fixed_dictionaries(
        {
            "path": st.text(min_size=1, max_size=20),
            "errors": severity,
            "warnings": severity,
            "information": severity,
            "diagnostics": st.just([]),
        },
    )
    folder_entry: st.SearchStrategy[dict[str, Any]] = st.fixed_dictionaries(
        {
            "path": st.text(min_size=1, max_size=20),
            "depth": st.integers(min_value=1, max_value=5),
            "errors": severity,
            "warnings": severity,
            "information": severity,
            "codeCounts": st.just({}),
            "recommendations": st.just([]),
        },
    )
    category_keys = st.sampled_from(
        ["unknownChecks", "optionalChecks", "unusedSymbols", "general"],
    )
    engine_opts: st.SearchStrategy[dict[str, Any]] = st.fixed_dictionaries(
        {
            "pluginArgs": st.lists(st.text(min_size=1, max_size=10), max_size=3),
            "include": st.lists(st.text(min_size=1, max_size=10), max_size=3),
            "exclude": st.lists(st.text(min_size=1, max_size=10), max_size=3),
            "overrides": st.just([]),
            "categoryMapping": st.dictionaries(
                keys=category_keys,
                values=st.lists(st.text(min_size=1, max_size=10), max_size=3),
                max_size=3,
            ),
        },
    )
    return st.fixed_dictionaries(
        {
            "tool": st.sampled_from(["pyright", "mypy"]),
            "mode": st.sampled_from(["current", "full"]),
            "command": st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5),
            "exitCode": st.integers(min_value=0, max_value=3),
            "durationMs": st.floats(
                min_value=0,
                max_value=1e6,
                allow_nan=False,
                allow_infinity=False,
            ),
            "summary": summary,
            "perFile": st.lists(file_entry, max_size=2),
            "perFolder": st.lists(folder_entry, max_size=2),
            "engineOptions": engine_opts,
        },
    )


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
@given(st.lists(_run_payloads(), min_size=0, max_size=3))
def test_h_manifest_valid_roundtrip(runs: list[dict[str, Any]]) -> None:
    manifest: dict[str, Any] = {"schemaVersion": CURRENT_MANIFEST_VERSION, "runs": runs}
    validated = validate_manifest_payload(manifest)
    assert "runs" in validated
    assert len(cast("Mapping[str, Any]", validated)["runs"]) == len(runs)


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
@given(
    st.lists(_run_payloads(), min_size=0, max_size=2),
    st.dictionaries(
        keys=st.text(min_size=1, max_size=8),
        values=st.integers(),
        min_size=1,
        max_size=2,
    ),
)
def test_h_manifest_rejects_unknown_top_level(
    runs: list[dict[str, Any]],
    extras: dict[str, int],
) -> None:
    # Ensure we include at least one extra key that is not among allowed fields
    for key in list(extras.keys()):
        if key in {
            "runs",
            "generatedAt",
            "projectRoot",
            "schemaVersion",
            "fingerprintTruncated",
            "toolVersions",
        }:
            del extras[key]
    if not extras:
        assume(False)
    manifest: dict[str, Any] = {"runs": runs}
    manifest["schemaVersion"] = CURRENT_MANIFEST_VERSION
    manifest.update(extras)
    with pytest.raises(ManifestValidationError):
        consume(validate_manifest_payload(manifest))
