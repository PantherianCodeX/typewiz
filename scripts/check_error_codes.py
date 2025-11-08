# Copyright (c) 2024 PantherianCodeX

"""Check error-code registry consistency against documentation."""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path

from typewiz._internal.error_codes import error_code_catalog


def _emit(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    _ = stream.write(f"{message}\n")


def _load_error_codes(src_path: Path) -> Iterable[str]:
    _ = sys.path.insert(0, str(src_path))
    return error_code_catalog().values()


def _discover_duplicates(codes: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for code in codes:
        if code in seen:
            duplicates.add(code)
        else:
            seen.add(code)
    return duplicates


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"

    try:
        codes = list(_load_error_codes(src_path))
    except RuntimeError as exc:
        _emit(f"[typewiz] {exc}", error=True)
        return 1

    duplicates = _discover_duplicates(codes)
    registry_codes = set(codes)

    doc_path = repo_root / "docs" / "EXCEPTIONS.md"
    if not doc_path.exists():
        _emit(f"[typewiz] documentation missing: {doc_path}", error=True)
        return 1

    content = doc_path.read_text(encoding="utf-8")
    documented_codes = set(re.findall(r"TW\d{3}", content))

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
            _emit(f"[typewiz] {line}", error=True)
        return 1

    _emit("[typewiz] error code registry and documentation are in sync")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
