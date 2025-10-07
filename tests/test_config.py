from __future__ import annotations

from pathlib import Path

from typewiz.api import _merge_configs
from typewiz.config import AuditConfig, EngineProfile, EngineSettings, load_config


def test_load_config_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "typewiz.toml"
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


def test_load_config_engine_profiles(tmp_path: Path) -> None:
    config_path = tmp_path / "typewiz.toml"
    config_path.write_text(
        """
[audit]
full_paths = ["src"]
plugin_args.stub = ["--base"]

[audit.active_profiles]
stub = "strict"

[audit.engines.stub]
plugin_args = ["--engine"]
include = ["extras"]

[audit.engines.stub.profiles.strict]
plugin_args = ["--strict"]
config_file = "configs/strict.json"
""",
        encoding="utf-8",
    )
    (config_path.parent / "configs").mkdir(exist_ok=True)
    (config_path.parent / "configs" / "strict.json").write_text("{}", encoding="utf-8")

    cfg = load_config(config_path)
    settings = cfg.audit.engine_settings["stub"]
    assert settings.plugin_args == ["--engine"]
    assert settings.include == ["extras"]
    assert settings.exclude == []
    assert settings.default_profile is None
    assert "strict" in settings.profiles
    strict = settings.profiles["strict"]
    assert strict.plugin_args == ["--strict"]
    assert strict.config_file == (config_path.parent / "configs" / "strict.json")
    assert cfg.audit.active_profiles == {"stub": "strict"}
    assert cfg.audit.plugin_args["stub"] == ["--base"]


def test_merge_config_adds_plugin_args() -> None:
    base = AuditConfig(plugin_args={"pyright": ["--foo"]})
    override = AuditConfig(plugin_args={"pyright": ["--bar"], "custom": ["--baz"]})
    merged = _merge_configs(base, override)
    assert merged.plugin_args["pyright"] == ["--foo", "--bar"]
    assert merged.plugin_args["custom"] == ["--baz"]


def test_merge_config_merges_engine_settings() -> None:
    base = AuditConfig(
        plugin_args={"stub": ["--global"]},
        engine_settings={
            "stub": EngineSettings(
                plugin_args=["--engine"],
                profiles={"strict": EngineProfile(plugin_args=["--strict"])}
            )
        },
        active_profiles={"stub": "strict"},
    )
    override = AuditConfig(
        plugin_args={"stub": ["--override"]},
        engine_settings={
            "stub": EngineSettings(
                plugin_args=["--engine-override"],
                default_profile="strict",
                profiles={
                    "strict": EngineProfile(plugin_args=["--stricter"]),
                    "lenient": EngineProfile(plugin_args=["--lenient"]),
                },
            )
        },
        active_profiles={"stub": "lenient"},
    )

    merged = _merge_configs(base, override)
    assert merged.plugin_args["stub"] == ["--global", "--override"]
    settings = merged.engine_settings["stub"]
    assert settings.plugin_args == ["--engine", "--engine-override"]
    assert settings.default_profile == "strict"
    assert settings.profiles["strict"].plugin_args == ["--strict", "--stricter"]
    assert settings.profiles["lenient"].plugin_args == ["--lenient"]
    assert merged.active_profiles["stub"] == "lenient"


def test_load_config_discovers_folder_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "typewiz.toml"
    config_path.write_text(
        """
config_version = 0

[audit]
full_paths = ["src"]
""",
        encoding="utf-8",
    )
    package_dir = tmp_path / "packages" / "billing"
    package_dir.mkdir(parents=True, exist_ok=True)
    override = package_dir / "typewiz.dir.toml"
    override.write_text(
        """
[active_profiles]
pyright = "strict"

[engines.pyright]
plugin_args = ["--project", "pyrightconfig.billing.json"]
include = ["."]
exclude = ["legacy"]
""",
        encoding="utf-8",
    )

    cfg = load_config(config_path)
    assert cfg.audit.path_overrides
    first = cfg.audit.path_overrides[0]
    assert first.path == package_dir
    assert first.active_profiles == {"pyright": "strict"}
    settings = first.engine_settings["pyright"]
    assert settings.plugin_args == ["--project", "pyrightconfig.billing.json"]
    # Include defaults to folder when "." used
    assert settings.include == ["."]
