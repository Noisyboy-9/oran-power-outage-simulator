from dataclasses import dataclass

from simulator.domain.ru import RUStatus
from simulator.environment.errors import EnvironmentValidationError


def _require_positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EnvironmentValidationError(f"{name} must be a positive integer")


def _require_positive_number(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not value > 0:
        raise EnvironmentValidationError(f"{name} must be positive")


@dataclass(frozen=True)
class MapConfig:
    width: int
    height: int

    def __post_init__(self) -> None:
        _require_positive_integer("width", self.width)
        _require_positive_integer("height", self.height)


@dataclass(frozen=True)
class RUConfig:
    count: int
    initial_battery: float
    initial_status: RUStatus
    active_consumption: float
    sleep_consumption: float
    coverage_radius: float

    def __post_init__(self) -> None:
        _require_positive_integer("count", self.count)
        _require_positive_number("coverage_radius", self.coverage_radius)


@dataclass(frozen=True)
class EnvironmentConfig:
    map: MapConfig
    ru: RUConfig
    user_count: int
    random_seed: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.map, MapConfig):
            raise EnvironmentValidationError("map must be a MapConfig")
        if not isinstance(self.ru, RUConfig):
            raise EnvironmentValidationError("ru must be an RUConfig")

        _require_positive_integer("user_count", self.user_count)

        entity_count = self.ru.count + self.user_count
        if entity_count > self.map.width * self.map.height:
            raise EnvironmentValidationError("entity count exceeds map capacity")

        if self.random_seed is not None and (
            isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int)
        ):
            raise EnvironmentValidationError("random_seed must be an integer or None")
