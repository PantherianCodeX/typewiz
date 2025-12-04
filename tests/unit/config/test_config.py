# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Config."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

import typewiz.config as config_module
import typewiz.config.models as config_models
from typewiz._internal.utils import consume
from typewiz.audit.options import merge_audit_configs
from typewiz.config import (
    AuditConfig,
    AuditConfigModel,
    ConfigFieldChoiceError,
    ConfigFieldTypeError,
    ConfigReadError,
    EngineProfile,
    EngineProfileModel,
    EngineSettings,
    EngineSettingsModel,
    InvalidConfigFileError,
    PathOverride,
    RatchetConfig,
    RatchetConfigModel,
    UnknownEngineProfileError,
    UnsupportedConfigVersionError,
    load_config,
)
from typewiz.core.model_types import FailOnPolicy, SeverityLevel, SignaturePolicy
from typewiz.core.type_aliases import EngineName, ProfileName, RunId, RunnerName

pytestmark = pytest.mark.unit

ensure_list = config_module.ensure_list
resolve_path_fields = config_module.resolve_path_fields

PYRIGHT = EngineName("pyright")
MYPY = EngineName("mypy")
STUB = EngineName("stub")
CUSTOM = EngineName("custom")
STRICT = ProfileName("strict")
LENIENT = ProfileName("lenient")


def test_load_config_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "typewiz.toml"
    consume(
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
        ),
    )
    cfg = load_config(config_path)
    assert cfg.audit.full_paths == ["apps", "packages"]
    assert cfg.audit.skip_full is True
    assert cfg.audit.max_depth == 5
    assert cfg.audit.dashboard_html == (config_path.parent / "reports" / "dashboard.html")
    assert cfg.audit.plugin_args[PYRIGHT] == ["--pythonversion", "3.12"]
    assert cfg.audit.runners == [RunnerName(PYRIGHT)]


def test_load_config_engine_profiles(tmp_path: Path) -> None:
    config_path = tmp_path / "typewiz.toml"
    consume(
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
        ),
    )
    (config_path.parent / "configs").mkdir(exist_ok=True)
    consume(
        (config_path.parent / "configs" / "strict.json").write_text("{}", encoding="utf-8"),
    )

    cfg = load_config(config_path)
    settings = cfg.audit.engine_settings[STUB]
    assert settings.plugin_args == ["--engine"]
    assert settings.include == ["extras"]
    assert settings.exclude == []
    assert settings.default_profile is None
    assert STRICT in settings.profiles
    strict = settings.profiles[STRICT]
    assert strict.plugin_args == ["--strict"]
    assert strict.config_file == (config_path.parent / "configs" / "strict.json")
    assert cfg.audit.active_profiles == {STUB: STRICT}
    assert cfg.audit.plugin_args[STUB] == ["--base"]


def test_merge_config_adds_plugin_args() -> None:
    base = AuditConfig(plugin_args={PYRIGHT: ["--foo"]})
    override = AuditConfig(plugin_args={PYRIGHT: ["--bar"], CUSTOM: ["--baz"]})
    merged = merge_audit_configs(base, override)
    assert merged.plugin_args[PYRIGHT] == ["--foo", "--bar"]
    assert merged.plugin_args[CUSTOM] == ["--baz"]


def test_merge_config_merges_engine_settings() -> None:
    base = AuditConfig(
        plugin_args={STUB: ["--global"]},
        engine_settings={
            STUB: EngineSettings(
                plugin_args=["--engine"],
                profiles={STRICT: EngineProfile(plugin_args=["--strict"])},
            ),
        },
        active_profiles={STUB: STRICT},
    )
    override = AuditConfig(
        plugin_args={STUB: ["--override"]},
        engine_settings={
            STUB: EngineSettings(
                plugin_args=["--engine-override"],
                default_profile=STRICT,
                profiles={
                    STRICT: EngineProfile(plugin_args=["--stricter"]),
                    LENIENT: EngineProfile(plugin_args=["--lenient"]),
                },
            ),
        },
        active_profiles={STUB: LENIENT},
    )

    merged = merge_audit_configs(base, override)
    assert merged.plugin_args[STUB] == ["--global", "--override"]
    settings = merged.engine_settings[STUB]
    assert settings.plugin_args == ["--engine", "--engine-override"]
    assert settings.default_profile == STRICT
    assert settings.profiles[STRICT].plugin_args == ["--strict", "--stricter"]
    assert settings.profiles[LENIENT].plugin_args == ["--lenient"]
    assert merged.active_profiles[STUB] == LENIENT


def test_load_config_discovers_folder_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "typewiz.toml"
    consume(
        config_path.write_text(
            """
config_version = 0

[audit]
full_paths = ["src"]
""",
            encoding="utf-8",
        ),
    )
    package_dir = tmp_path / "packages" / "billing"
    package_dir.mkdir(parents=True, exist_ok=True)
    override = package_dir / "typewiz.dir.toml"
    consume(
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
        ),
    )

    cfg = load_config(config_path)
    assert cfg.audit.path_overrides
    first = cfg.audit.path_overrides[0]
    assert first.path == package_dir
    assert first.active_profiles == {PYRIGHT: STRICT}
    settings = first.engine_settings[PYRIGHT]
    assert settings.plugin_args == ["--project", "pyrightconfig.billing.json"]
    # Include defaults to folder when "." used
    assert settings.include == ["."]


def test_load_config_defaults_without_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    expected = sorted([RunnerName(MYPY), RunnerName(PYRIGHT)])
    assert sorted(cfg.audit.runners or []) == expected
    assert cfg.audit.full_paths is None


def test_load_config_raises_for_unknown_default_profile(tmp_path: Path) -> None:
    config_path = tmp_path / "typewiz.toml"
    consume(
        config_path.write_text(
            """
[audit]
runners = ["stub"]

[audit.engines.stub]
default_profile = "strict"
""",
            encoding="utf-8",
        ),
    )
    with pytest.raises(ValueError):
        consume(load_config(config_path))


def test_load_config_normalises_policy_enums(tmp_path: Path) -> None:
    config_path = tmp_path / "typewiz.toml"
    consume(
        config_path.write_text(
            """
[audit]
fail_on = "WARNINGS"

[ratchet]
signature = "ignore"
""",
            encoding="utf-8",
        ),
    )

    cfg = load_config(config_path)
    assert cfg.audit.fail_on is FailOnPolicy.WARNINGS
    assert cfg.ratchet.signature is SignaturePolicy.IGNORE


def test_directory_override_validation_error_message(tmp_path: Path) -> None:
    error = config_models.DirectoryOverrideValidationError(tmp_path, ValueError("boom"))
    assert str(error).startswith(f"Invalid typewiz directory override in {tmp_path}")


def test_engine_profile_model_requires_string_inherit() -> None:
    invalid_value: object = object()
    with pytest.raises(ValidationError, match="inherit must be a string"):
        _ = EngineProfileModel(inherit=cast(str, invalid_value))


def test_engine_settings_model_requires_string_default_profile() -> None:
    invalid_value: object = object()
    with pytest.raises(ValidationError, match="default_profile must be a string"):
        _ = EngineSettingsModel(default_profile=cast(str, invalid_value))


def test_audit_config_model_coerces_limits_and_fail_on() -> None:
    model = AuditConfigModel.model_validate({"max_depth": "5", "fail_on": "errors"})
    assert model.max_depth == 5
    assert model.fail_on is FailOnPolicy.ERRORS
    with pytest.raises(ValidationError, match="fail_on must be one of"):
        _ = AuditConfigModel.model_validate({"fail_on": "unknown"})
    with pytest.raises(ValidationError, match="fail_on must be a string"):
        _ = AuditConfigModel.model_validate({"fail_on": 123})


def test_audit_config_model_coerces_plugin_args_non_dict() -> None:
    model = AuditConfigModel.model_validate({"plugin_args": ["not-a-dict"]})
    assert model.plugin_args == {}


def test_ratchet_config_model_coerces_targets_and_signature() -> None:
    model = RatchetConfigModel.model_validate({
        "targets": {"error": "4", "warn": True, "bad": "x"},
        "signature": "warn",
    })
    assert model.targets["error"] == 4
    assert model.targets["warn"] == 1
    assert "bad" not in model.targets
    assert model.signature is SignaturePolicy.WARN
    with pytest.raises(ValidationError, match="ratchet\\.signature must be one of"):
        _ = RatchetConfigModel.model_validate({"signature": "invalid"})
    with pytest.raises(ValidationError, match="ratchet\\.signature must be a string"):
        _ = RatchetConfigModel.model_validate({"signature": 123})


def test_config_model_rejects_unknown_version() -> None:
    with pytest.raises(ValidationError, match="Unsupported config_version"):
        _ = config_models.ConfigModel(config_version=999)


def test_ensure_list_variants() -> None:
    assert ensure_list(None) is None
    assert ensure_list("  item  ") == ["item"]
    assert ensure_list(42) == []
    assert ensure_list(["a", "", "b "]) == ["a", "b"]


def test_engine_profile_model_strips_inherit() -> None:
    profile = EngineProfileModel.model_validate(
        {"inherit": " base ", "plugin_args": ["--x", "--x"]},
    )
    assert profile.inherit == "base"
    assert profile.plugin_args == ["--x"]
    with pytest.raises(ValueError):
        consume(EngineProfileModel.model_validate({"inherit": 123}))


def test_engine_settings_model_validators() -> None:
    model = EngineSettingsModel.model_validate(
        {
            "default_profile": " strict ",
            "plugin_args": ["--a", "--a"],
            "profiles": {" strict ": {"plugin_args": ["--p"]}},
        },
    )
    assert model.default_profile == "strict"
    assert model.profiles["strict"].plugin_args == ["--p"]
    with pytest.raises(ValueError):
        consume(EngineSettingsModel.model_validate({"default_profile": 123}))
    with pytest.raises(ValueError):
        consume(
            EngineSettingsModel.model_validate(
                {
                    "default_profile": "missing",
                    "profiles": {"strict": {"plugin_args": []}},
                },
            ),
        )


def test_audit_config_model_plugin_args_normalisation() -> None:
    model = AuditConfigModel.model_validate(
        {
            "plugin_args": {"pyright": ["--x", "--x"], "": ["ignored"]},
            "active_profiles": {" stub ": " strict "},
            "engines": {" stub ": {"profiles": {"strict": {}}}},
        },
    )
    assert model.plugin_args == {"pyright": ["--x"]}
    assert model.active_profiles == {"stub": "strict"}
    with pytest.raises(ValueError):
        consume(
            AuditConfigModel.model_validate(
                {
                    "active_profiles": {"stub": "missing"},
                    "engines": {"stub": {"profiles": {}}},
                },
            ),
        )


def test_resolve_path_fields_resolves_relative_paths(tmp_path: Path) -> None:
    config_file = Path("configs/strict.json")
    override_config = Path("strict_override.json")
    (tmp_path / "configs").mkdir(exist_ok=True)
    consume((tmp_path / "configs" / "strict.json").write_text("{}", encoding="utf-8"))
    (tmp_path / "pkg").mkdir(exist_ok=True)
    audit = AuditConfig(
        manifest_path=Path("manifest.json"),
        dashboard_json=Path("dash.json"),
        engine_settings={
            STUB: EngineSettings(
                config_file=config_file,
                profiles={STRICT: EngineProfile(config_file=config_file)},
            ),
        },
        path_overrides=[
            PathOverride(
                path=Path("pkg"),
                engine_settings={
                    STUB: EngineSettings(
                        config_file=override_config,
                        profiles={STRICT: EngineProfile(config_file=override_config)},
                    ),
                },
            ),
        ],
    )
    resolve_path_fields(tmp_path, audit)
    assert audit.manifest_path == (tmp_path / "manifest.json").resolve()
    stub_settings = audit.engine_settings[STUB]
    assert stub_settings.config_file and stub_settings.config_file.is_absolute()
    override = audit.path_overrides[0]
    assert override.path.is_absolute()
    override_settings = override.engine_settings[STUB]
    assert override_settings.config_file and override_settings.config_file.is_absolute()


def test_ratchet_config_model_converts_severity_strings() -> None:
    model = RatchetConfigModel.model_validate({"severities": ["error", "information"]})
    assert model.severities == [SeverityLevel.ERROR, SeverityLevel.INFORMATION]


def test_ratchet_config_model_defaults_when_empty() -> None:
    model = RatchetConfigModel.model_validate({"severities": []})
    assert model.severities == [SeverityLevel.ERROR, SeverityLevel.WARNING]


def test_ratchet_config_runs_coerced_to_run_id() -> None:
    model = RatchetConfigModel.model_validate({"runs": ["pyright:current", "  mypy:full  "]})
    assert model.runs == [RunId("pyright:current"), RunId("mypy:full")]
    config = RatchetConfig(
        runs=[RunId("pyright:current "), RunId("mypy:full")],
    )
    assert config.runs == [RunId("pyright:current"), RunId("mypy:full")]


def test_ensure_list_behaviour() -> None:
    assert ensure_list(" value ") == ["value"]
    assert ensure_list(["a", "b"]) == ["a", "b"]
    assert ensure_list(123) == []
    assert ensure_list(None) is None


def test_ratchet_config_post_init_strips_runs() -> None:
    cfg = RatchetConfig(runs=[RunId("pyright:current"), RunId("")])
    assert cfg.runs == [RunId("pyright:current")]


def test_audit_config_post_init_coerces_keys() -> None:
    cfg = AuditConfig(
        plugin_args={EngineName("pyright"): ["--foo"]},
        active_profiles={EngineName("pyright"): ProfileName("strict")},
    )
    assert list(cfg.plugin_args) == [EngineName("pyright")]
    assert cfg.active_profiles == {EngineName("pyright"): ProfileName("strict")}


def test_audit_config_model_coercions() -> None:
    model = AuditConfigModel.model_validate({
        "fail_on": "warnings",
        "plugin_args": {"pyright": ["--foo", "--foo"]},
        "engines": {
            "pyright": {
                "profiles": {"strict": {"plugin_args": ["--strict"]}},
            }
        },
        "active_profiles": {"pyright": "strict"},
        "full_paths": "src",
    })
    assert model.fail_on is FailOnPolicy.WARNINGS
    assert model.plugin_args == {"pyright": ["--foo"]}
    assert model.full_paths == ["src"]


def test_audit_config_model_invalid_fail_on() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _ = AuditConfigModel.model_validate({"fail_on": "unsupported"})
    assert "fail_on must be one of" in str(excinfo.value)


def test_config_exception_messages(tmp_path: Path) -> None:
    assert "must be one of" in str(ConfigFieldChoiceError("field", ("a", "b")))
    assert "must be a string" in str(ConfigFieldTypeError("field"))
    assert "default_profile" in str(ConfigFieldChoiceError("default_profile", ("strict",)))
    assert "Unknown profile" in str(UnknownEngineProfileError("pyright", "strict"))
    assert "Unsupported config_version" in str(UnsupportedConfigVersionError(2, 0))
    assert "Unable to read" in str(ConfigReadError(tmp_path / "cfg.toml", OSError("boom")))
    assert "Invalid typewiz" in str(
        InvalidConfigFileError(tmp_path / "cfg.toml", ValueError("bad"))
    )
