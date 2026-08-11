import logging
import math
from collections.abc import Hashable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Final

import yaml

from simulator.configuration.errors import ConfigurationError
from simulator.configuration.models import (
    ApplicationConfig,
    ControllerConfig,
    ControllerKind,
    LoggingConfig,
    MetricKind,
    MetricsConfig,
    SimulationConfig,
    TimestampConfig,
)
from simulator.domain.ru import RUStatus
from simulator.environment import (
    EnvironmentConfig,
    EnvironmentValidationError,
    MapConfig,
    RUConfig,
)

_STANDARD_LOGGING_LEVELS: Final = MappingProxyType(
    {
        "CRITICAL": logging.CRITICAL,
        "FATAL": logging.FATAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "WARN": logging.WARN,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
)


class _DuplicateKeyError(yaml.YAMLError):
    """Carry the dotted path of a duplicate YAML key to ``load_config``.

    PyYAML reports generic parsing errors but otherwise silently overwrites a
    duplicate mapping key. This internal exception preserves the precise key
    path so the public loader can raise a useful ``ConfigurationError``.
    """

    def __init__(self, path: str) -> None:
        self.path = path


class _DuplicateKeySafeLoader(yaml.SafeLoader):
    """Safely construct YAML mappings while rejecting duplicate keys.

    ``yaml.SafeLoader`` prevents unsafe object construction, but it accepts
    duplicate mapping keys and keeps only the final value. Configuration files
    must instead fail fast, so this loader detects duplicates before a value is
    overwritten and records dotted paths for nested mappings.
    """

    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self.mapping_paths: dict[int, str] = {}

    def construct_mapping(
        self, node: yaml.MappingNode, deep: bool = False
    ) -> dict[object, object]:
        path = self.mapping_paths.pop(id(node), "")
        mapping: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            key_path = _join_path(path, str(key))
            if not isinstance(key, Hashable):
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found unhashable key",
                    key_node.start_mark,
                )
            if key in mapping:
                raise _DuplicateKeyError(key_path)
            if isinstance(value_node, yaml.MappingNode):
                self.mapping_paths[id(value_node)] = key_path
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_config(path: Path) -> ApplicationConfig:
    """Load an application configuration from a YAML file."""
    raw_config = _load_mapping(path)
    _require_exact_keys(
        raw_config, {"environment", "controller", "logging", "simulation"}, ""
    )
    return ApplicationConfig(
        environment=_parse_environment(raw_config["environment"], "environment"),
        controller=_parse_controller(raw_config["controller"], "controller"),
        logging=_parse_logging(raw_config["logging"], "logging"),
        simulation=_parse_simulation(raw_config["simulation"], "simulation"),
    )


def _load_mapping(path: Path) -> Mapping[object, object]:
    try:
        raw_config = yaml.load(
            path.read_text(encoding="utf-8"), Loader=_DuplicateKeySafeLoader
        )
    except OSError as error:
        raise ConfigurationError(
            f"configuration file {path} does not exist or cannot be read"
        ) from error
    except _DuplicateKeyError as error:
        raise ConfigurationError(f"{error.path}: duplicate key") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(
            f"configuration file {path} contains invalid YAML"
        ) from error

    if raw_config is None:
        raise ConfigurationError("configuration file is empty")
    return _require_mapping(raw_config, "configuration")


def _parse_environment(value: object, path: str) -> EnvironmentConfig:
    raw_environment = _require_mapping(value, path)
    _require_exact_keys(
        raw_environment, {"map", "ru", "user_count", "random_seed"}, path
    )

    map_path = _join_path(path, "map")
    raw_map = _require_mapping(raw_environment["map"], map_path)
    _require_exact_keys(raw_map, {"width", "height"}, map_path)
    map_config = _construct(
        MapConfig,
        map_path,
        width=_require_positive_integer(
            raw_map["width"], _join_path(map_path, "width")
        ),
        height=_require_positive_integer(
            raw_map["height"], _join_path(map_path, "height")
        ),
    )

    ru_path = _join_path(path, "ru")
    raw_ru = _require_mapping(raw_environment["ru"], ru_path)
    _require_exact_keys(
        raw_ru,
        {
            "count",
            "initial_battery",
            "initial_status",
            "zero_user_consumption",
            "one_user_consumption",
            "multi_user_consumption_per_user",
            "sleep_consumption",
            "user_capacity",
            "coverage_radius",
        },
        ru_path,
    )
    ru_config = _construct(
        RUConfig,
        ru_path,
        count=_require_positive_integer(raw_ru["count"], _join_path(ru_path, "count")),
        initial_battery=_require_positive_number(
            raw_ru["initial_battery"], _join_path(ru_path, "initial_battery")
        ),
        initial_status=_parse_ru_status(
            raw_ru["initial_status"], _join_path(ru_path, "initial_status")
        ),
        zero_user_consumption=_require_positive_number(
            raw_ru["zero_user_consumption"],
            _join_path(ru_path, "zero_user_consumption"),
        ),
        one_user_consumption=_require_positive_number(
            raw_ru["one_user_consumption"],
            _join_path(ru_path, "one_user_consumption"),
        ),
        multi_user_consumption_per_user=_require_positive_number(
            raw_ru["multi_user_consumption_per_user"],
            _join_path(ru_path, "multi_user_consumption_per_user"),
        ),
        sleep_consumption=_require_positive_number(
            raw_ru["sleep_consumption"], _join_path(ru_path, "sleep_consumption")
        ),
        user_capacity=_require_positive_integer(
            raw_ru["user_capacity"], _join_path(ru_path, "user_capacity")
        ),
        coverage_radius=_require_positive_number(
            raw_ru["coverage_radius"], _join_path(ru_path, "coverage_radius")
        ),
    )

    return _construct(
        EnvironmentConfig,
        path,
        map=map_config,
        ru=ru_config,
        user_count=_require_positive_integer(
            raw_environment["user_count"], _join_path(path, "user_count")
        ),
        random_seed=_require_int_or_none(
            raw_environment["random_seed"], _join_path(path, "random_seed")
        ),
    )


def _parse_controller(value: object, path: str) -> ControllerConfig:
    raw_controller = _require_mapping(value, path)
    kind_path = _join_path(path, "kind")
    _require_known_keys(raw_controller, {"kind", "threshold_percentage"}, path)
    if "kind" not in raw_controller:
        raise ConfigurationError(f"{kind_path}: missing required key")
    kind_name = _require_string(raw_controller["kind"], kind_path)
    try:
        kind = ControllerKind(kind_name)
    except ValueError as error:
        raise ConfigurationError(f"{kind_path}: unsupported controller kind") from error

    if kind is ControllerKind.THRESHOLD_STAGGERED_ACTIVE:
        _require_exact_keys(raw_controller, {"kind", "threshold_percentage"}, path)
        threshold_path = _join_path(path, "threshold_percentage")
        threshold = _require_number(
            raw_controller["threshold_percentage"], threshold_path
        )
    else:
        _require_exact_keys(raw_controller, {"kind"}, path)
        threshold = None

    return _construct(
        ControllerConfig,
        _join_path(path, "threshold_percentage"),
        kind=kind,
        threshold_percentage=threshold,
    )


def _parse_simulation(value: object, path: str) -> SimulationConfig:
    raw_simulation = _require_mapping(value, path)
    _require_exact_keys(raw_simulation, {"steps", "metrics"}, path)
    metrics_path = _join_path(path, "metrics")
    raw_metrics = _require_mapping(raw_simulation["metrics"], metrics_path)
    _require_exact_keys(
        raw_metrics,
        {
            "collectors",
            "minimum_emergency_service_fraction",
            "minimum_service_link_weight",
        },
        metrics_path,
    )
    collectors_path = _join_path(metrics_path, "collectors")
    raw_collectors = _require_sequence(raw_metrics["collectors"], collectors_path)
    collectors: list[MetricKind] = []
    for raw_collector in raw_collectors:
        collector_name = _require_string(raw_collector, collectors_path)
        try:
            collectors.append(MetricKind(collector_name))
        except ValueError as error:
            raise ConfigurationError(
                f"{collectors_path}: unsupported metric kind"
            ) from error
    if len(set(collectors)) != len(collectors):
        raise ConfigurationError(
            f"{collectors_path}: collectors must not contain duplicates"
        )
    return _construct(
        SimulationConfig,
        path,
        steps=_require_positive_integer(raw_simulation["steps"], f"{path}.steps"),
        metrics=_construct(
            MetricsConfig,
            metrics_path,
            validation_paths={
                "minimum_emergency_service_fraction": _join_path(
                    metrics_path, "minimum_emergency_service_fraction"
                ),
                "minimum_service_link_weight": _join_path(
                    metrics_path, "minimum_service_link_weight"
                ),
            },
            collectors=tuple(collectors),
            minimum_emergency_service_fraction=_require_number(
                raw_metrics["minimum_emergency_service_fraction"],
                _join_path(metrics_path, "minimum_emergency_service_fraction"),
            ),
            minimum_service_link_weight=_require_number(
                raw_metrics["minimum_service_link_weight"],
                _join_path(metrics_path, "minimum_service_link_weight"),
            ),
        ),
    )


def _parse_logging(value: object, path: str) -> LoggingConfig:
    raw_logging = _require_mapping(value, path)
    _require_exact_keys(
        raw_logging,
        {
            "logger_name",
            "level",
            "destination",
            "format",
            "include_logger_name",
            "include_log_level",
            "timestamp",
            "cache_loggers_on_first_use",
            "propagate",
        },
        path,
    )

    timestamp_path = _join_path(path, "timestamp")
    raw_timestamp = _require_mapping(raw_logging["timestamp"], timestamp_path)
    _require_exact_keys(raw_timestamp, {"key", "format", "utc"}, timestamp_path)
    timestamp_format = _require_string(
        raw_timestamp["format"], _join_path(timestamp_path, "format")
    )
    if timestamp_format != "iso":
        raise ConfigurationError(
            f"{_join_path(timestamp_path, 'format')}: only 'iso' is supported"
        )
    utc = _require_boolean(raw_timestamp["utc"], _join_path(timestamp_path, "utc"))
    if not utc:
        raise ConfigurationError(f"{_join_path(timestamp_path, 'utc')}: must be true")

    destination = _require_string(
        raw_logging["destination"], _join_path(path, "destination")
    )
    if destination != "stdout":
        raise ConfigurationError(
            f"{_join_path(path, 'destination')}: only 'stdout' is supported"
        )
    renderer_format = _require_string(raw_logging["format"], _join_path(path, "format"))
    if renderer_format != "json":
        raise ConfigurationError(
            f"{_join_path(path, 'format')}: only 'json' is supported"
        )

    return LoggingConfig(
        logger_name=_require_string(
            raw_logging["logger_name"], _join_path(path, "logger_name")
        ),
        level=_parse_logging_level(raw_logging["level"], _join_path(path, "level")),
        destination=destination,
        format=renderer_format,
        include_logger_name=_require_boolean(
            raw_logging["include_logger_name"], _join_path(path, "include_logger_name")
        ),
        include_log_level=_require_boolean(
            raw_logging["include_log_level"], _join_path(path, "include_log_level")
        ),
        timestamp=TimestampConfig(
            key=_require_string(
                raw_timestamp["key"], _join_path(timestamp_path, "key")
            ),
            format=timestamp_format,
            utc=utc,
        ),
        cache_loggers_on_first_use=_require_boolean(
            raw_logging["cache_loggers_on_first_use"],
            _join_path(path, "cache_loggers_on_first_use"),
        ),
        propagate=_require_boolean(
            raw_logging["propagate"], _join_path(path, "propagate")
        ),
    )


def _parse_ru_status(value: object, path: str) -> RUStatus:
    status_name = _require_string(value, path)
    try:
        return RUStatus(status_name)
    except ValueError as error:
        raise ConfigurationError(f"{path}: unsupported RU status") from error


def _parse_logging_level(value: object, path: str) -> int:
    level_name = _require_string(value, path)
    level = _STANDARD_LOGGING_LEVELS.get(level_name)
    if level is None:
        raise ConfigurationError(f"{path}: unsupported logging level")
    return level


def _construct[T](
    constructor: type[T],
    path: str,
    /,
    validation_paths: Mapping[str, str] | None = None,
    **kwargs: object,
) -> T:
    try:
        return constructor(**kwargs)
    except EnvironmentValidationError as error:
        raise ConfigurationError(f"{path}: {error}") from error
    except ValueError as error:
        error_path = path
        if validation_paths is not None:
            error_path = next(
                (
                    validation_path
                    for field_name, validation_path in validation_paths.items()
                    if str(error).startswith(field_name)
                ),
                path,
            )
        raise ConfigurationError(f"{error_path}: {error}") from error


def _require_mapping(value: object, path: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{path}: must be a mapping")
    return value


def _require_sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ConfigurationError(f"{path}: must be a list")
    return value


def _require_exact_keys(
    values: Mapping[object, object], expected_keys: set[str], path: str
) -> None:
    _require_known_keys(values, expected_keys, path)
    for key in expected_keys:
        if key not in values:
            raise ConfigurationError(f"{_join_path(path, key)}: missing required key")


def _require_known_keys(
    values: Mapping[object, object], allowed_keys: set[str], path: str
) -> None:
    for key in values:
        if not isinstance(key, str) or key not in allowed_keys:
            raise ConfigurationError(f"{_join_path(path, str(key))}: unknown key")


def _require_string(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{path}: must be a string")
    return value


def _require_boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{path}: must be a boolean")
    return value


def _require_positive_integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{path}: must be a positive integer")
    return value


def _require_positive_number(value: object, path: str) -> int | float:
    number = _require_number(value, path)
    if not number > 0:
        raise ConfigurationError(f"{path}: must be positive")
    return number


def _require_number(value: object, path: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{path}: must be a number")
    if not math.isfinite(value):
        raise ConfigurationError(f"{path}: must be a finite number")
    return value


def _require_int_or_none(value: object, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{path}: must be an integer or null")
    return value


def _join_path(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key
