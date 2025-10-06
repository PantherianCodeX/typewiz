from __future__ import annotations

from pathlib import Path

from pytc.api import _merge_configs
from pytc.config import AuditConfig, load_config


def test_load_config_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "pytc.toml"
    config_path.write_text(
        """
[audit]
full_paths = ["apps", "packages"]
skip_full = true
max_depth = 5
runners = ["pyright"]
plugin_args.pyright = ["--pythonversion", "3.12"]
dashboard_html = "reports/dashboard.html"
""",
        encoding="utf-8",
    )
    cfg = load_config(config_path)
    assert cfg.audit.full_paths == ["apps", "packages"]
    assert cfg.audit.skip_full is True
    assert cfg.audit.max_depth == 5
    assert cfg.audit.dashboard_html == (config_path.parent / "reports" / "dashboard.html")
    assert cfg.audit.plugin_args["pyright"] == ["--pythonversion", "3.12"]
    assert cfg.audit.runners == ["pyright"]


def test_merge_config_adds_plugin_args() -> None:
    base = AuditConfig(plugin_args={"pyright": ["--foo"]})
    override = AuditConfig(plugin_args={"pyright": ["--bar"], "custom": ["--baz"]})
    merged = _merge_configs(base, override)
    assert merged.plugin_args["pyright"] == ["--foo", "--bar"]
    assert merged.plugin_args["custom"] == ["--baz"]
