# Exception Reference

Typewiz raises a small set of structured exceptions to make it easy to handle
errors programmatically. Each exception maps to a stable error code (see
`typewiz._internal.error_codes.error_code_for`) which can be used in logs or CI.

Core exceptions:

- `typewiz._internal.exceptions.TypewizError` — base for all Typewiz errors. Code: `TW000`.
- `typewiz._internal.exceptions.TypewizValidationError` — validation failures. Code: `TW100`.
- `typewiz._internal.exceptions.TypewizTypeError` — type mismatches at runtime. Code: `TW101`.

Configuration errors (`typewiz.config`):

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

- `typewiz.manifest_models.ManifestValidationError` — Pydantic validation failure. Code: `TW300`.
- `typewiz.manifest.versioning.InvalidManifestRunsError` — `runs` must be a list. Code: `TW301`.
- `typewiz.manifest.versioning.UnsupportedManifestVersionError` — unknown `schemaVersion`. Code: `TW302`.
- `typewiz.manifest.versioning.InvalidManifestVersionTypeError` — bad `schemaVersion` type. Code: `TW303`.

Dashboard errors:

- `typewiz.dashboard.DashboardTypeError` — invalid dashboard input types. Code: `TW200`.

Readiness errors:

- `typewiz.readiness.views.ReadinessValidationError` — readiness payload contained invalid data. Code: `TW201`.

Usage tips:

- Prefer catching specific exceptions when you can; fall back to `TypewizError` for a single broad handler.
- Use `error_code_for(exc)` to map an exception instance to a code for logs or user messages.
- CLI commands already map known exceptions to exit codes and friendly messages.
