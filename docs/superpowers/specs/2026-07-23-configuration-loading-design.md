# Configuration Loading Design

## Goal

Load one YAML configuration file at application setup into immutable, typed
configuration objects, then pass each component the configuration it owns.
Configuration parsing must remain separate from environment construction,
controller behavior, and logging behavior.

## Package Structure

Add a dedicated `simulator.configuration` package:

```text
src/simulator/configuration/
├── __init__.py
├── errors.py
├── loader.py
└── models.py
```

`simulator.configuration` publicly exports `ApplicationConfig`,
`ConfigurationError`, `ControllerConfig`, `ControllerKind`, `LoggingConfig`,
`TimestampConfig`, and `load_config`.

The existing `MapConfig`, `RUConfig`, and `EnvironmentConfig` stay in
`simulator.environment.config`. They are environment-facing models and remain
free of YAML and filesystem concerns. `ApplicationConfig.environment` contains
an `EnvironmentConfig` instance.

## Configuration Models

All configuration models are frozen dataclasses. They are ordinary objects,
not a module-level singleton and not stored in a hidden global variable.

```python
@dataclass(frozen=True)
class ApplicationConfig:
    environment: EnvironmentConfig
    controller: ControllerConfig
    logging: LoggingConfig


class ControllerKind(StrEnum):
    ALWAYS_ACTIVE = "always_active"
    STAGGERED_ACTIVE = "staggered_active"
    THRESHOLD_STAGGERED_ACTIVE = "threshold_staggered_active"


@dataclass(frozen=True)
class ControllerConfig:
    kind: ControllerKind
    threshold_percentage: float | None = None


@dataclass(frozen=True)
class TimestampConfig:
    key: str
    format: str
    utc: bool


@dataclass(frozen=True)
class LoggingConfig:
    logger_name: str
    level: int
    destination: str
    format: str
    include_logger_name: bool
    include_log_level: bool
    timestamp: TimestampConfig
    cache_loggers_on_first_use: bool
    propagate: bool
```

`ControllerConfig` accepts `threshold_percentage` only when `kind` is
`threshold_staggered_active`. That percentage must use the same inclusive
`0` to `100` range as `ThresholdStaggeredActiveController`. The always-active
and staggered controller kinds reject the threshold field rather than silently
ignoring it.

The initial YAML schema changes the current `controllers` mapping to one
`controller` mapping. It must select exactly one policy:

```yaml
controller:
  kind: threshold_staggered_active
  threshold_percentage: 50.0
```

This configuration does not expose the current ten-timestamp stagger interval:
it is still controller behavior rather than an approved configuration setting.

## Loading and Validation

`load_config(path: Path) -> ApplicationConfig` is the only public file-loading
function. It reads UTF-8 YAML through `yaml.safe_load`; it never instantiates
arbitrary Python objects from configuration.

The loader rejects a missing, unreadable, empty, non-mapping, malformed, or
structurally invalid document with `ConfigurationError`. It also rejects
unknown keys at every schema level so spelling mistakes cannot quietly fall
back to defaults. Error messages identify the failing dotted path, such as
`environment.ru.count` or `logging.timestamp.utc`.

All keys in `default.yaml` are required. The YAML `null` value is accepted for
`environment.random_seed`; integer seed values, including zero and negative
values, are passed to `EnvironmentConfig`. The loader converts
`environment.ru.initial_status` from its YAML string to `RUStatus`, and
converts a standard logging level name such as `INFO` to its integer logging
level. It then delegates existing environment validation to the immutable
environment config models. Invalid values originating there are wrapped in
`ConfigurationError` with their configuration path.

Logging configuration mirrors currently supported behavior. The only accepted
destination is `stdout`, the only accepted renderer format is `json`, and the
only accepted timestamp format is `iso`. `timestamp.utc` must be true because
the current logger always uses UTC timestamps. These constrained values keep
the YAML honest: a setting is accepted only when the application can honor it.

## Component Wiring

The eventual application setup/composition root owns the returned
`ApplicationConfig` and explicitly creates components:

```python
config = load_config(config_path)

configure_logging(config.logging)
environment = Environment(config.environment)
controller = build_controller(config.controller)
```

`configure_logging` changes from a zero-argument function to
`configure_logging(config: LoggingConfig) -> None`. Its implementation uses
the supplied values for the logger name, level, output destination, JSON
renderer, processors, timestamp, cache behavior, and propagation behavior.

`build_controller(config: ControllerConfig) -> RUController` is a focused
factory in `simulator.configuration`. It returns the configured existing
controller class and passes `threshold_percentage` only to
`ThresholdStaggeredActiveController`. It does not update RUs or own an
environment.

No component reaches into a global configuration object or reads a file. Tests
can construct typed configs directly, while integration tests exercise
`load_config` with temporary YAML files.

## Dependencies and Documentation

Add `PyYAML` as a runtime dependency using `uv add pyyaml`; commit the matching
`pyproject.toml` and `uv.lock` changes. Update `configs/default.yaml` to use
the singular `controller` mapping and a selected controller kind. Update the
README with a file-based setup example and the configuration module's public
entry point.

## Testing

Tests under `tests/configuration/` cover successful parsing of the default
configuration, every controller kind, invalid controller combinations,
conversion of RU status and logging level, invalid or missing files, malformed
or empty YAML, non-mapping YAML roots, unknown keys, validation errors with
dotted paths, and the public imports.

Logging tests verify that the passed `LoggingConfig` controls the named logger's
level, propagation, and output target without asserting timestamp contents.
Controller-factory tests verify the selected controller class and its threshold
configuration. The full pytest suite, Ruff lint, Ruff format check, and Git
whitespace check must pass.

## Scope Boundaries

This change does not create a CLI, load configuration implicitly at import
time, add environment-variable overrides, add multiple-file inheritance,
support secrets, cache loaded files, add new simulation settings, or change
environment and controller semantics beyond making their existing settings
available through the YAML file.
