from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:  # Python 3.11+
    import tomllib as toml  # type: ignore[assignment]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as toml  # type: ignore[assignment]


@dataclass(slots=True)
class AuditConfig:
    manifest_path: Path | None = None
    full_paths: list[str] | None = None
    max_depth: int | None = None
    skip_current: bool | None = None
    skip_full: bool | None = None
    pyright_only: bool | None = None
    mypy_only: bool | None = None
    pyright_args: list[str] = field(default_factory=list)
    mypy_args: list[str] = field(default_factory=list)
    fail_on: str | None = None
    dashboard_json: Path | None = None
    dashboard_markdown: Path | None = None
    dashboard_html: Path | None = None


@dataclass(slots=True)
class ToolArgs:
    pyright: list[str] = field(default_factory=list)
    mypy: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Config:
    audit: AuditConfig = field(default_factory=AuditConfig)


def _as_path(base: Path, value: str | None) -> Path | None:
    if value is None or value == "":
        return None
    candidate = Path(value)
    return candidate if candidate.is_absolute() else (base / candidate)


def _list_of_str(data: Any) -> list[str] | None:
    if data is None:
        return None
    if isinstance(data, (list, tuple, set)):
        values = []
        for item in data:
            if isinstance(item, str):
                candidate = item.strip()
                if candidate:
                    values.append(candidate)
        return values
    if isinstance(data, str):
        candidate = data.strip()
        return [candidate] if candidate else []
    return None


def _load_audit_config(base: Path, raw: dict[str, Any]) -> AuditConfig:
    audit = AuditConfig()
    audit.manifest_path = _as_path(base, raw.get("manifest_path"))
    audit.full_paths = _list_of_str(raw.get("full_paths"))
    audit.max_depth = int(raw["max_depth"]) if raw.get("max_depth") is not None else None
    if raw.get("skip_current") is not None:
        audit.skip_current = bool(raw["skip_current"])
    if raw.get("skip_full") is not None:
        audit.skip_full = bool(raw["skip_full"])
    if raw.get("pyright_only") is not None:
        audit.pyright_only = bool(raw["pyright_only"])
    if raw.get("mypy_only") is not None:
        audit.mypy_only = bool(raw["mypy_only"])
    audit.pyright_args = _list_of_str(raw.get("pyright_args")) or []
    audit.mypy_args = _list_of_str(raw.get("mypy_args")) or []
    fail_on = raw.get("fail_on")
    if isinstance(fail_on, str):
        audit.fail_on = fail_on.lower().strip()
    audit.dashboard_json = _as_path(base, raw.get("dashboard_json"))
    audit.dashboard_markdown = _as_path(base, raw.get("dashboard_markdown"))
    audit.dashboard_html = _as_path(base, raw.get("dashboard_html"))
    return audit


def load_config(explicit_path: Path | None = None) -> Config:
    search_order: list[Path] = []
    if explicit_path:
        search_order.append(explicit_path)
    else:
        search_order.append(Path("typing_inspector.toml"))
        search_order.append(Path(".typing_inspector.toml"))

    for candidate in search_order:
        if not candidate.exists():
            continue
        data = toml.loads(candidate.read_text(encoding="utf-8"))
        if "tool" in data and isinstance(data["tool"], dict):
            tool_section = data["tool"].get("typing_inspector")
            if isinstance(tool_section, dict):
                data = tool_section
        base = candidate.parent.resolve()
        audit_raw = data.get("audit") if isinstance(data, dict) else None
        audit = _load_audit_config(base, audit_raw) if isinstance(audit_raw, dict) else AuditConfig()
        return Config(audit=audit)

    return Config()
