from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    sys.path.insert(0, str(src_path))

    try:
        from typewiz.error_codes import error_code_catalog
    except Exception as exc:  # pragma: no cover - script usage guard
        print(f"[typewiz] failed to import error_code_catalog: {exc}")
        return 1

    catalog = error_code_catalog()
    codes = list(catalog.values())

    duplicates: set[str] = set()
    seen: set[str] = set()
    for code in codes:
        if code in seen:
            duplicates.add(code)
        else:
            seen.add(code)

    doc_path = repo_root / "docs" / "EXCEPTIONS.md"
    if not doc_path.exists():
        print(f"[typewiz] documentation missing: {doc_path}")
        return 1
    content = doc_path.read_text(encoding="utf-8")
    documented_codes = set(re.findall(r"TW\d{3}", content))
    registry_codes = set(seen)

    missing_in_docs = registry_codes - documented_codes
    orphaned_codes = documented_codes - registry_codes

    status_lines = []
    if duplicates:
        status_lines.append("duplicate codes in registry: " + ", ".join(sorted(duplicates)))
    if missing_in_docs:
        status_lines.append("missing codes in docs: " + ", ".join(sorted(missing_in_docs)))
    if orphaned_codes:
        status_lines.append("unknown codes in docs: " + ", ".join(sorted(orphaned_codes)))

    if status_lines:
        for line in status_lines:
            print(f"[typewiz] {line}")
        return 1

    print("[typewiz] error code registry and documentation are in sync")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
