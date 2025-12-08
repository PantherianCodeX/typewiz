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

"""Unit tests for Misc Import Guardrails."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CLI_ROOT = Path("src/ratchetr/cli")
DOMAIN_ROOTS = [
    Path("src/ratchetr/core"),
    Path("src/ratchetr/dashboard"),
    Path("src/ratchetr/audit"),
    Path("src/ratchetr/engines"),
    Path("src/ratchetr/config"),
    Path("src/ratchetr/manifest"),
    Path("src/ratchetr/ratchet"),
    Path("src/ratchetr/readiness"),
    Path("src/ratchetr/services"),
]


def _collect_internal_imports(source: Path) -> list[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            offenders.extend(alias.name for alias in node.names if alias.name.startswith("ratchetr._internal"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("ratchetr._internal"):
                offenders.append(module)
    return offenders


def test_cli_does_not_import_internal_modules() -> None:
    offenders: dict[Path, list[str]] = {}
    for path in CLI_ROOT.rglob("*.py"):
        imports = _collect_internal_imports(path)
        if imports:
            offenders[path] = imports
    assert not offenders, f"CLI modules must not import ratchetr._internal: {offenders}"


def test_domain_modules_use_public_shims() -> None:
    offenders: dict[Path, list[str]] = {}
    for root in DOMAIN_ROOTS:
        for path in root.rglob("*.py"):
            imports = _collect_internal_imports(path)
            if imports:
                offenders[path] = imports
    assert not offenders, f"Domain modules must use shims instead of ratchetr._internal: {offenders}"
