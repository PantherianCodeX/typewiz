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

"""Runtime tests for the ``ratchetr.compat`` helpers."""

from __future__ import annotations

import builtins
import datetime as _dt
import enum as _enum
import importlib
import sys
import typing as _typing
from types import ModuleType

import pytest
import typing_extensions as _typing_extensions

from ratchetr.compat import (
    UTC,
    StrEnum,
    TypeAliasType,
    TypedDict,
    assert_never,
    override,
    tomllib,
)
from ratchetr.compat import datetime as compat_datetime
from ratchetr.compat import enums as compat_enums
from ratchetr.compat import toml as compat_toml
from ratchetr.compat import typing as compat_typing

pytestmark = pytest.mark.unit


class _CompatEnumsModule(_typing.Protocol):
    """Protocol describing the compat.enums module."""

    StrEnum: type[StrEnum]


class _EnumModule(ModuleType):
    """Fake enum module for testing stdlib fallback."""

    Enum: type[_enum.Enum] = _enum.Enum

    # ignore JUSTIFIED: AttributeError trampoline exists solely to satisfy type checking;
    # behaviour is exercised via the public compat helpers
    def __getattr__(self, name: str) -> object:  # pragma: no cover - typing only
        raise AttributeError(name)


class Colour(StrEnum):
    """Sample enum used to validate StrEnum behaviour."""

    RED = "red"
    BLUE = "blue"


def test_strenum_behaves_like_string_enum() -> None:
    """StrEnum should behave as both ``str`` and ``Enum``."""
    assert issubclass(Colour, (str,))
    assert Colour.RED.value == "red"
    instance = Colour("blue")
    assert isinstance(instance, Colour)
    assert instance is Colour.BLUE


def test_utc_timezone_matches_stdlib() -> None:
    """UTC helper should point at a zero-offset timezone."""
    assert UTC is compat_datetime.UTC
    assert UTC.utcoffset(None) == _dt.timedelta(0)
    aware = _dt.datetime.now(tz=UTC)
    assert aware.tzinfo is UTC


def test_tomllib_proxy_can_parse_documents() -> None:
    """Tomllib proxy should parse TOML payloads."""
    assert tomllib is compat_toml.tomllib
    parsed: dict[str, object] = tomllib.loads('name = "ratchetr"\n[tool]\ncount = 1\n')
    tool_table = _typing.cast("dict[str, object]", parsed["tool"])
    assert parsed["name"] == "ratchetr"
    assert tool_table["count"] == 1


def test_typing_exports_are_available() -> None:
    """Typing aliases should be importable and functional."""
    assert compat_typing.TypedDict is TypedDict
    example_alias = TypeAliasType("example_alias", list[int])
    assert example_alias.__value__ == list[int]

    class Payload(TypedDict):
        foo: int

    payload: Payload = {"foo": 1}
    assert payload["foo"] == 1

    class Greeter:
        def greet(self) -> str:
            return f"hello from {self.__class__.__name__}"

    class EnthusiasticGreeter(Greeter):
        @override
        def greet(self) -> str:
            return f"HELLO from {self.__class__.__name__}"

    assert EnthusiasticGreeter().greet().startswith("HELLO")
    with pytest.raises(AssertionError):
        assert_never("invalid")


def test_package_reexports_match_module_symbols() -> None:
    """ratchetr.compat should mirror module-level exports."""
    assert UTC is compat_datetime.UTC
    assert StrEnum is compat_enums.StrEnum
    assert tomllib is compat_toml.tomllib


def test_strenum_creates_compat_when_stdlib_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """compat.enums should build a compat StrEnum when stdlib lacks it."""
    fake_enum = _EnumModule("enum")
    fake_enum.Enum = _enum.Enum
    # intentionally omit StrEnum to trigger ImportError
    monkeypatch.setitem(sys.modules, "enum", fake_enum)

    reloaded = _typing.cast("_CompatEnumsModule", importlib.reload(compat_enums))
    try:
        compat_str_enum: type[StrEnum] = compat_enums.StrEnum
        assert reloaded.StrEnum is compat_str_enum
        assert compat_str_enum.__name__ == "_CompatStrEnum"
        assert issubclass(compat_str_enum, (str, _enum.Enum))
        assert compat_str_enum.__mro__[0] is compat_str_enum
        assert str in compat_str_enum.__mro__
        assert _enum.Enum in compat_str_enum.__mro__

        class TestEnum(compat_enums.StrEnum):
            FOO = "foo"
            BAR = "bar"

        assert TestEnum.FOO.value == "foo"
        assert isinstance(TestEnum.FOO, str)
        assert str(TestEnum.BAR) == "bar"
    finally:
        importlib.reload(compat_enums)


def test_tomllib_falls_back_to_tomli(monkeypatch: pytest.MonkeyPatch) -> None:
    """compat.toml should use tomli when stdlib tomllib is unavailable."""
    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> ModuleType:
        if name == "tomllib":
            error_message = "tomllib not available"
            raise ModuleNotFoundError(error_message)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    reloaded = importlib.reload(compat_toml)
    try:
        assert reloaded.tomllib.__name__ == "tomli"
        parsed = reloaded.tomllib.loads('answer = 42\n[section]\nkey = "value"\n')
        assert parsed["answer"] == 42
        assert parsed["section"]["key"] == "value"
    finally:
        importlib.reload(compat_toml)


def test_typing_imports_fall_back_to_typing_extensions(monkeypatch: pytest.MonkeyPatch) -> None:
    """compat.typing should import symbols from typing_extensions when stdlib lacks them."""
    monkeypatch.delattr(_typing, "TypeAliasType", raising=False)
    monkeypatch.delattr(_typing, "TypedDict", raising=False)
    monkeypatch.delattr(_typing, "override", raising=False)

    reloaded = importlib.reload(compat_typing)
    try:
        assert reloaded.TypeAliasType is _typing_extensions.TypeAliasType
        assert reloaded.TypedDict is _typing_extensions.TypedDict
        assert reloaded.override is _typing_extensions.override
    finally:
        importlib.reload(compat_typing)
