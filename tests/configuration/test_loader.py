import logging
from pathlib import Path

import pytest

from simulator.configuration import (
    ConfigurationError,
    ControllerKind,
    MetricKind,
    load_config,
)
from simulator.domain.ru import RUStatus

DEFAULT_CONTROLLER = (
    "controller:\n  kind: threshold_staggered_active\n  threshold_percentage: 50.0\n"
)

VALID_YAML = """\
environment:
  map:
    width: 3
    height: 3
  ru:
    count: 5
    initial_battery: 100.0
    initial_status: active
    active_consumption: 2.0
    sleep_consumption: 0.5
    coverage_radius: 1.0
  user_count: 4
  random_seed: 42
controller:
  kind: threshold_staggered_active
  threshold_percentage: 50.0
simulation:
  steps: 3
  metrics:
    collectors:
      - average_emergency_qos
      - network_lifetime
    minimum_emergency_service_fraction: 0.8
logging:
  logger_name: simulator
  level: INFO
  destination: stdout
  format: json
  include_logger_name: true
  include_log_level: true
  timestamp:
    key: logged_at
    format: iso
    utc: true
  cache_loggers_on_first_use: true
  propagate: false
"""


def write_config(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(contents, encoding="utf-8")
    return path


def test_loads_typed_configuration(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, VALID_YAML))

    assert config.environment.ru.initial_status is RUStatus.ACTIVE
    assert config.logging.level == logging.INFO
    assert config.controller.kind is ControllerKind.THRESHOLD_STAGGERED_ACTIVE


def test_loads_simulation_steps(tmp_path: Path) -> None:
    assert load_config(write_config(tmp_path, VALID_YAML)).simulation.steps == 3


def test_loads_ordered_metrics_configuration(tmp_path: Path) -> None:
    metrics = load_config(write_config(tmp_path, VALID_YAML)).simulation.metrics

    assert metrics.collectors == (
        MetricKind.AVERAGE_EMERGENCY_QOS,
        MetricKind.NETWORK_LIFETIME,
    )
    assert metrics.minimum_emergency_service_fraction == 0.8


@pytest.mark.parametrize(
    ("contents", "path"),
    [
        (
            VALID_YAML.replace(
                (
                    "    collectors:\n"
                    "      - average_emergency_qos\n"
                    "      - network_lifetime"
                ),
                "    collectors: invalid",
            ),
            "simulation.metrics.collectors",
        ),
        (
            VALID_YAML.replace("      - network_lifetime", "      - unknown_metric"),
            "simulation.metrics.collectors",
        ),
        (
            VALID_YAML.replace(
                "      - network_lifetime", "      - average_emergency_qos"
            ),
            "simulation.metrics.collectors",
        ),
        (
            VALID_YAML.replace(
                "minimum_emergency_service_fraction: 0.8",
                "minimum_emergency_service_fraction: 0",
            ),
            "simulation.metrics.minimum_emergency_service_fraction",
        ),
        (
            VALID_YAML.replace(
                "minimum_emergency_service_fraction: 0.8",
                "minimum_emergency_service_fraction: 1.1",
            ),
            "simulation.metrics.minimum_emergency_service_fraction",
        ),
        (
            VALID_YAML.replace(
                "minimum_emergency_service_fraction: 0.8",
                "minimum_emergency_service_fraction: true",
            ),
            "simulation.metrics.minimum_emergency_service_fraction",
        ),
    ],
)
def test_rejects_invalid_metrics_configuration(
    tmp_path: Path, contents: str, path: str
) -> None:
    with pytest.raises(ConfigurationError, match=path):
        load_config(write_config(tmp_path, contents))


@pytest.mark.parametrize(
    ("contents", "path"),
    [
        (
            VALID_YAML.replace(
                (
                    "    collectors:\n"
                    "      - average_emergency_qos\n"
                    "      - network_lifetime"
                ),
                "    collectors: []",
            ),
            "simulation.metrics.collectors",
        ),
        (
            VALID_YAML.replace("      - network_lifetime", "      - 1"),
            "simulation.metrics.collectors",
        ),
        (
            VALID_YAML.replace(
                "    minimum_emergency_service_fraction: 0.8",
                "    minimum_emergency_service_fraction: 0.8\n    unknown: value",
            ),
            "simulation.metrics.unknown",
        ),
        (
            VALID_YAML.replace(
                (
                    "  metrics:\n"
                    "    collectors:\n"
                    "      - average_emergency_qos\n"
                    "      - network_lifetime\n"
                    "    minimum_emergency_service_fraction: 0.8\n"
                ),
                "",
            ),
            "simulation.metrics",
        ),
    ],
)
def test_rejects_invalid_metrics_structure(
    tmp_path: Path, contents: str, path: str
) -> None:
    with pytest.raises(ConfigurationError, match=path):
        load_config(write_config(tmp_path, contents))


@pytest.mark.parametrize("steps", ["0", "-1", "true", "1.5"])
def test_rejects_invalid_simulation_steps(tmp_path: Path, steps: str) -> None:
    contents = VALID_YAML.replace("steps: 3", f"steps: {steps}")

    with pytest.raises(ConfigurationError, match="simulation.steps"):
        load_config(write_config(tmp_path, contents))


def test_loads_tracked_default_configuration() -> None:
    config_path = Path(__file__).parents[2] / "configs" / "default.yaml"

    config = load_config(config_path)

    assert config.environment.map.width == 20
    assert config.controller.kind is ControllerKind.THRESHOLD_STAGGERED_ACTIVE
    assert config.logging.level == logging.INFO


def test_rejects_unknown_nested_key(tmp_path: Path) -> None:
    path = write_config(
        tmp_path, VALID_YAML.replace("count: 5", "count: 5\n    cout: 6")
    )

    with pytest.raises(ConfigurationError, match="environment.ru.cout"):
        load_config(path)


def test_rejects_duplicate_root_key(tmp_path: Path) -> None:
    contents = VALID_YAML + VALID_YAML.split("controller:", maxsplit=1)[0]

    with pytest.raises(ConfigurationError, match=r"^environment: duplicate key$"):
        load_config(write_config(tmp_path, contents))


def test_rejects_duplicate_nested_key(tmp_path: Path) -> None:
    contents = VALID_YAML.replace("    count: 5", "    count: 5\n    count: 5")

    with pytest.raises(
        ConfigurationError, match=r"^environment.ru.count: duplicate key$"
    ):
        load_config(write_config(tmp_path, contents))


def test_rejects_mapping_with_unhashable_key(tmp_path: Path) -> None:
    contents = "? [a, b]\n: value\n"

    with pytest.raises(ConfigurationError):
        load_config(write_config(tmp_path, contents))


def test_rejects_custom_registered_logging_level(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = VALID_YAML.replace("level: INFO", "level: TRACE")

    with monkeypatch.context() as local_logging:
        local_logging.setattr(logging, "_nameToLevel", logging._nameToLevel.copy())
        local_logging.setattr(logging, "_levelToName", logging._levelToName.copy())
        logging.addLevelName(5, "TRACE")

        with pytest.raises(
            ConfigurationError, match=r"^logging.level: unsupported logging level$"
        ):
            load_config(write_config(tmp_path, contents))


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_config(tmp_path / "missing.yaml")


@pytest.mark.parametrize("contents", ["environment: [", "", "[]"])
def test_rejects_malformed_empty_and_non_mapping_documents(
    tmp_path: Path, contents: str
) -> None:
    with pytest.raises(ConfigurationError):
        load_config(write_config(tmp_path, contents))


def test_rejects_missing_required_key_with_path(tmp_path: Path) -> None:
    path = write_config(tmp_path, VALID_YAML.replace("  user_count: 4\n", ""))

    with pytest.raises(ConfigurationError, match="environment.user_count"):
        load_config(path)


@pytest.mark.parametrize(
    ("replacement", "path"),
    [
        ("initial_status: unavailable", "environment.ru.initial_status"),
        ("level: LOUD", "logging.level"),
        ("destination: file", "logging.destination"),
        ("  format: plain", "logging.format"),
        ("    format: epoch", "logging.timestamp.format"),
        ("    utc: false", "logging.timestamp.utc"),
    ],
)
def test_rejects_invalid_enum_and_unsupported_logging_values(
    tmp_path: Path, replacement: str, path: str
) -> None:
    original = {
        "initial_status: unavailable": "initial_status: active",
        "level: LOUD": "level: INFO",
        "destination: file": "destination: stdout",
        "  format: plain": "  format: json",
        "    format: epoch": "    format: iso",
        "    utc: false": "    utc: true",
    }[replacement]
    contents = VALID_YAML.replace(original, replacement)

    with pytest.raises(ConfigurationError, match=path):
        load_config(write_config(tmp_path, contents))


@pytest.mark.parametrize(
    ("contents", "path"),
    [
        (VALID_YAML.replace("width: 3", "width: 0"), "environment.map.width"),
        (
            VALID_YAML.replace("coverage_radius: 1.0", "coverage_radius: false"),
            "environment.ru.coverage_radius",
        ),
        (
            VALID_YAML.replace("initial_battery: 100.0", "initial_battery: 0"),
            "environment.ru.initial_battery",
        ),
        (
            VALID_YAML.replace("active_consumption: 2.0", "active_consumption: false"),
            "environment.ru.active_consumption",
        ),
        (
            VALID_YAML.replace("sleep_consumption: 0.5", "sleep_consumption: 0"),
            "environment.ru.sleep_consumption",
        ),
        (
            VALID_YAML.replace("initial_battery: 100.0", "initial_battery: .nan"),
            "environment.ru.initial_battery",
        ),
        (VALID_YAML.replace("user_count: 4", "user_count: 5"), "environment"),
    ],
)
def test_rejects_environment_validation_errors_with_paths(
    tmp_path: Path, contents: str, path: str
) -> None:
    with pytest.raises(ConfigurationError, match=path):
        load_config(write_config(tmp_path, contents))


@pytest.mark.parametrize(
    ("kind", "threshold"),
    [
        ("always_active", None),
        ("staggered_active", None),
        ("threshold_staggered_active", 25),
    ],
)
def test_loads_each_controller_kind(
    tmp_path: Path, kind: str, threshold: int | None
) -> None:
    controller = f"controller:\n  kind: {kind}\n"
    if threshold is not None:
        controller += f"  threshold_percentage: {threshold}\n"
    contents = VALID_YAML.replace(DEFAULT_CONTROLLER, controller)

    config = load_config(write_config(tmp_path, contents))

    assert config.controller.kind.value == kind
    assert config.controller.threshold_percentage == threshold


@pytest.mark.parametrize(
    ("controller", "path"),
    [
        (
            "controller:\n  kind: threshold_staggered_active\n",
            "controller.threshold_percentage",
        ),
        (
            "controller:\n  kind: always_active\n  threshold_percentage: 50\n",
            "controller.threshold_percentage",
        ),
        (
            "controller:\n  kind: staggered_active\n  threshold_percentage: 50\n",
            "controller.threshold_percentage",
        ),
        (
            "controller:\n  kind: threshold_staggered_active\n"
            "  threshold_percentage: 101\n",
            "controller.threshold_percentage",
        ),
    ],
)
def test_rejects_invalid_controller_combinations(
    tmp_path: Path, controller: str, path: str
) -> None:
    contents = VALID_YAML.replace(DEFAULT_CONTROLLER, controller)

    with pytest.raises(ConfigurationError, match=path):
        load_config(write_config(tmp_path, contents))
