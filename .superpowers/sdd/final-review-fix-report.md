# Final Review Fix Report

## Scope

Addressed the final whole-branch review findings for configuration loading:

- YAML duplicate keys are rejected at both root and nested mappings with the
  responsible dotted configuration path.
- Logging levels are validated against a fixed standard-level mapping rather
  than mutable runtime logging registrations.

## TDD Evidence

Added these regression tests in `tests/configuration/test_loader.py` before
changing the loader:

- `test_rejects_duplicate_root_key`
- `test_rejects_duplicate_nested_key`
- `test_rejects_custom_registered_logging_level`

The initial red run used:

```text
uv run pytest tests/configuration/test_loader.py::test_rejects_duplicate_root_key tests/configuration/test_loader.py::test_rejects_duplicate_nested_key tests/configuration/test_loader.py::test_rejects_custom_registered_logging_level -v
```

It collected three tests and all three failed: duplicate root and nested keys
were silently accepted by `yaml.safe_load`, while a `TRACE` level added through
`logging.addLevelName(5, "TRACE")` was accepted through
`logging.getLevelNamesMapping()`.

## Implementation

- Added `_DuplicateKeySafeLoader`, a `yaml.SafeLoader` subclass that tracks
  mapping paths and raises `_DuplicateKeyError` before any duplicate can
  overwrite a prior value.
- Wrapped that error as `ConfigurationError("<dotted path>: duplicate key")`.
- Replaced the mutable logging-level lookup with an explicit immutable
  `MappingProxyType` containing standard logging level names and values.

## Verification

All commands were run from the `feature/configuration-loading` worktree:

```text
uv run pytest tests/configuration/test_loader.py -v
# 31 passed

uv run pytest
# 162 passed

uv run ruff check .
# All checks passed!

uv run ruff format --check .
# 44 files already formatted

git diff --check
# no output; exit 0
```

The complete pytest suite was also rerun after the final formatting adjustment:

```text
uv run pytest
# 162 passed
```
