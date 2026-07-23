from dataclasses import dataclass
from enum import StrEnum

from simulator.environment import EnvironmentConfig


class ControllerKind(StrEnum):
    ALWAYS_ACTIVE = "always_active"
    STAGGERED_ACTIVE = "staggered_active"
    THRESHOLD_STAGGERED_ACTIVE = "threshold_staggered_active"


@dataclass(frozen=True)
class ControllerConfig:
    kind: ControllerKind
    threshold_percentage: float | None = None

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
class ApplicationConfig:
    environment: EnvironmentConfig
    controller: ControllerConfig
    logging: LoggingConfig
