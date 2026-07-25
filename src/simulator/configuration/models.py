from dataclasses import dataclass
from enum import StrEnum

from simulator.environment import EnvironmentConfig


class ControllerKind(StrEnum):
    ALWAYS_ACTIVE = "always_active"
    STAGGERED_ACTIVE = "staggered_active"
    THRESHOLD_STAGGERED_ACTIVE = "threshold_staggered_active"


class MetricKind(StrEnum):
    AVERAGE_EMERGENCY_QOS = "average_emergency_qos"
    AVERAGE_RU_BATTERY_DEPLETION_TIME = "average_ru_battery_depletion_time"
    NETWORK_LIFETIME = "network_lifetime"


@dataclass(frozen=True)
class MetricsConfig:
    collectors: tuple[MetricKind, ...]
    minimum_emergency_service_fraction: float
    minimum_service_link_weight: float

    def __post_init__(self) -> None:
        if not isinstance(self.collectors, tuple) or any(
            not isinstance(kind, MetricKind) for kind in self.collectors
        ):
            raise ValueError("collectors must contain MetricKind values")
        if len(set(self.collectors)) != len(self.collectors):
            raise ValueError("collectors must not contain duplicates")
        fraction = self.minimum_emergency_service_fraction
        if (
            isinstance(fraction, bool)
            or not isinstance(fraction, (int, float))
            or not 0 < fraction <= 1
        ):
            raise ValueError(
                "minimum_emergency_service_fraction must be a number between 0 and 1"
            )
        threshold = self.minimum_service_link_weight
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not 0 <= threshold <= 1
        ):
            raise ValueError(
                "minimum_service_link_weight must be a number between 0 and 1"
            )


@dataclass(frozen=True)
class ControllerConfig:
    kind: ControllerKind
    threshold_percentage: int | float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ControllerKind):
            raise ValueError("kind must be a ControllerKind")

        is_threshold_controller = self.kind is ControllerKind.THRESHOLD_STAGGERED_ACTIVE
        if not is_threshold_controller and self.threshold_percentage is not None:
            raise ValueError(
                "threshold_percentage is only supported by threshold_staggered_active"
            )

        threshold = self.threshold_percentage
        if is_threshold_controller and (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not 0 <= threshold <= 100
        ):
            raise ValueError("threshold_percentage must be a number between 0 and 100")


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


@dataclass(frozen=True)
class SimulationConfig:
    steps: int
    metrics: MetricsConfig

    def __post_init__(self) -> None:
        if (
            isinstance(self.steps, bool)
            or not isinstance(self.steps, int)
            or self.steps <= 0
        ):
            raise ValueError("steps must be a positive integer")


@dataclass(frozen=True)
class ApplicationConfig:
    environment: EnvironmentConfig
    controller: ControllerConfig
    logging: LoggingConfig
    simulation: SimulationConfig
