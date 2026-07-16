# Structured JSON Logging Design

## Goal

Use `structlog` for all simulator logging and provide one hard-coded startup
configuration that emits INFO-and-higher events as newline-delimited JSON.

## Scope

- Add `structlog` as a runtime dependency through uv.
- Add one public `configure_logging()` function in a focused logging module.
- Migrate all existing simulator loggers and log events from the standard
  library to `structlog`.
- Keep controller state coverage without asserting logging behavior.
- Do not maintain tests for logging configuration, formatting, filtering, or
  event emission.
- Keep user-facing setup documentation for the logging behavior.

This change does not add environment-based configuration, configuration
objects, alternate development renderers, log files, or integrations for
third-party packages that use standard-library logging.

## Architecture

`src/simulator/logging.py` owns logging configuration. Its
`configure_logging() -> None` function configures `structlog` with a hard-coded
INFO threshold, UTC ISO timestamps under `logged_at`, log levels, logger names,
JSON rendering, and standard output. A future executable or CLI must call this
function once at application startup; importing `simulator` must not configure
global logging as a side effect. Loggers are assembled and cached on first use
because runtime configuration is fixed after application startup.

Modules that emit events obtain a module-local logger with
`structlog.get_logger(__name__)`. They do not configure logging and do not
import or share a mutable logger instance from the configuration module.

## Existing Log Migration

The staggered and threshold-staggered controllers currently report failed RU
activation through standard-library logging. Both sites will emit the same
structured INFO event through `structlog`:

- `event`: `ru_activation_failed`
- `controller`: the controller class name
- `ru_id`: the selected RU identifier
- `timestamp`: the simulation timestamp
- `battery`: the RU's current battery
- `required_battery`: the active-consumption requirement

The always-active controller continues not to log an underpowered RU because
its existing behavior explicitly requires no log for that case.

## Output Behavior

After startup configuration, each accepted event is written to standard output
as one JSON object per line. INFO, WARNING, ERROR, and CRITICAL events are
accepted; DEBUG events are filtered out. Each rendered event contains its event
name, structured domain fields, log level, logger name, and UTC `logged_at`
timestamp. The log timestamp uses its own key so domain events can retain a
simulation `timestamp` field.

## Testing

Logging is treated as infrastructure and is intentionally not covered by the
test suite. Tests do not assert JSON formatting, levels, timestamps, logger
names, event emission, or absence of events.

Controller tests retain state-only coverage for scenarios that also happen to
emit logs, such as selected underpowered RUs being placed into sleep state. The
dedicated logging test module and `structlog.testing.capture_logs()` usage are
removed.

## Documentation

`README.md` will show that an application entry point must call
`configure_logging()` once before running the simulator and that module code
should use `structlog.get_logger(__name__)` with structured keyword fields.
