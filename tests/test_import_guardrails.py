from __future__ import annotations

import ast
from pathlib import Path

CLI_ROOT = Path("src/typewiz/cli")
DOMAIN_ROOTS = [
    Path("src/typewiz/core"),
    Path("src/typewiz/dashboard"),
    Path("src/typewiz/audit"),
    Path("src/typewiz/engines"),
    Path("src/typewiz/config"),
    Path("src/typewiz/manifest"),
    Path("src/typewiz/ratchet"),
    Path("src/typewiz/readiness"),
    Path("src/typewiz/services"),
]


def _collect_internal_imports(source: Path) -> list[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("typewiz._internal"):
                    offenders.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("typewiz._internal"):
                offenders.append(module)
    return offenders


def test_cli_does_not_import_internal_modules() -> None:
    offenders: dict[Path, list[str]] = {}
    for path in CLI_ROOT.rglob("*.py"):
        imports = _collect_internal_imports(path)
        if imports:
            offenders[path] = imports
    assert not offenders, f"CLI modules must not import typewiz._internal: {offenders}"


def test_domain_modules_use_public_shims() -> None:
    offenders: dict[Path, list[str]] = {}
    for root in DOMAIN_ROOTS:
        for path in root.rglob("*.py"):
            imports = _collect_internal_imports(path)
            if imports:
                offenders[path] = imports
    assert not offenders, f"Domain modules must use shims instead of typewiz._internal: {offenders}"
