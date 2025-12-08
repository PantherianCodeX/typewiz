# Exception Reference

ratchetr raises a small set of structured exceptions to make it easy to handle errors programmatically. Each exception maps to a stable error code (see `ratchetr.error_codes.error_code_for`) which can be used in logs or CI.

Core exceptions:

- `ratchetr.exceptions.RatchetrError` — base for all Ratchetr errors. Code: `TW000`.
- `ratchetr.exceptions.RatchetrValidationError` — validation failures. Code: `TW100`.
- `ratchetr.exceptions.RatchetrTypeError` — type mismatches at runtime. Code: `TW101`.

Configuration errors (`ratchetr.config`):

- `ConfigValidationError` — generic config validation error. Code: `TW110`.
- `ConfigFieldTypeError` — wrong type for a field (e.g., string expected). Code: `TW111`.
- `ConfigFieldChoiceError` — invalid value; lists allowed choices. Code: `TW112`.
- `UndefinedDefaultProfileError` — missing default profile. Code: `TW113`.
- `UnknownEngineProfileError` — referenced engine profile not found. Code: `TW114`.
- `UnsupportedConfigVersionError` — unsupported `config_version`. Code: `TW115`.
- `ConfigReadError` — config file could not be read. Code: `TW116`.
- `DirectoryOverrideValidationError` — invalid directory override manifest. Code: `TW117`.
- `InvalidConfigFileError` — invalid root configuration file. Code: `TW118`.

Manifest and schema errors:

- `ratchetr.manifest.models.ManifestValidationError` — Pydantic validation failure. Code: `TW300`.
- `ratchetr.manifest.versioning.InvalidManifestRunsError` — `runs` must be a list. Code: `TW301`.
- `ratchetr.manifest.versioning.UnsupportedManifestVersionError` — unknown `schemaVersion`. Code: `TW302`.
- `ratchetr.manifest.versioning.InvalidManifestVersionTypeError` — bad `schemaVersion` type. Code: `TW303`.

Dashboard errors:

- `ratchetr.dashboard.DashboardTypeError` — invalid dashboard input types. Code: `TW200`.

Readiness errors:

- `ratchetr.readiness.views.ReadinessValidationError` — readiness payload contained invalid data. Code: `TW201`.

Usage tips:

- Prefer catching specific exceptions when you can; fall back to `RatchetrError` for a single broad handler.
- Use `error_code_for(exc)` to map an exception instance to a code for logs or user messages.
- CLI commands already map known exceptions to exit codes and friendly messages.
