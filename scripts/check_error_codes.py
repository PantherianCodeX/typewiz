#!/usr/bin/env python3
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

"""Check error-code registry consistency against documentation.

This script must work whether the package is installed or not. It prepends the
repo's `src/` directory to `sys.path` before importing internal modules.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def _emit(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    _ = stream.write(f"{message}\n")


def _load_error_codes(src_path: Path) -> Iterable[str]:
    src_str = str(src_path)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    module = importlib.import_module("ratchetr._infra.error_codes")
    error_catalog = module.error_code_catalog()
    return [str(code) for code in error_catalog.values()]


def _load_documented_codes(doc_path: Path) -> set[str]:
    """Load the set of documented error codes from the exceptions guide.

    Args:
        doc_path: Path to `EXCEPTIONS.md` containing the public registry.

    Returns:
        Set of error-code strings (e.g., `"TW001"`) discovered in the
        documentation.

    Raises:
        FileNotFoundError: If the documentation file is missing.
    """
    if not doc_path.exists():
        msg = f"documentation missing: {doc_path}"
        raise FileNotFoundError(msg)
    content = doc_path.read_text(encoding="utf-8")
    return set(re.findall(r"TW\d{3}", content))


def _discover_duplicates(codes: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for code in codes:
        if code in seen:
            duplicates.add(code)
        else:
            seen.add(code)
    return duplicates


def main(argv: Sequence[str] | None = None) -> int:
    """Validate that the error-code registry matches the public docs.

    Args:
        argv: Optional CLI arguments (ignored; present for parity with entrypoints).

    Returns:
        `0` if the registry and documentation list identical codes; `1` if
        duplicate, missing, or orphaned codes are detected.
    """
    if argv:
        _emit("[ratchetr] check_error_codes does not accept CLI arguments; ignoring argv")

    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"

    try:
        codes = list(_load_error_codes(src_path))
    except RuntimeError as exc:
        _emit(f"[ratchetr] {exc}", error=True)
        return 1

    doc_path = repo_root / "docs" / "EXCEPTIONS.md"
    try:
        documented_codes = _load_documented_codes(doc_path)
    except FileNotFoundError as exc:
        _emit(f"[ratchetr] {exc}", error=True)
        return 1

    duplicates = _discover_duplicates(codes)
    registry_codes = set(codes)

    missing_in_docs = registry_codes - documented_codes
    orphaned_codes = documented_codes - registry_codes

    status_lines: list[str] = []
    if duplicates:
        status_lines.append("duplicate codes in registry: " + ", ".join(sorted(duplicates)))
    if missing_in_docs:
        status_lines.append("missing codes in docs: " + ", ".join(sorted(missing_in_docs)))
    if orphaned_codes:
        status_lines.append("unknown codes in docs: " + ", ".join(sorted(orphaned_codes)))

    if status_lines:
        for line in status_lines:
            _emit(f"[ratchetr] {line}", error=True)
        return 1

    _emit("[ratchetr] error code registry and documentation are in sync")
    return 0


# ignore JUSTIFIED: CLI entrypoint is trivial and only used when invoking the
# script directly; logic is fully covered by unit tests
if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
