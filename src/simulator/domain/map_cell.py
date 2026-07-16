from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from simulator.domain.errors import DomainValidationError
from simulator.domain.ru import RU
from simulator.domain.user import User


@dataclass(frozen=True)
class MapCell:
    x: int
    y: int
    occupant: RU | User | None = None

    def __post_init__(self) -> None:
        coordinates = {"x": self.x, "y": self.y}
        for name, value in coordinates.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise DomainValidationError(
                    f"{name} coordinate must be a non-negative integer"
                )

        if self.occupant is not None and not isinstance(self.occupant, (RU, User)):
            raise DomainValidationError("occupant must be an RU, User, or None")

    def distance_to(self, other: MapCell) -> float:
        return hypot(self.x - other.x, self.y - other.y)
