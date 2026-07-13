from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from simulator.domain.errors import DomainValidationError


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def __post_init__(self) -> None:
        if self.x < 0:
            raise DomainValidationError("x must be non-negative")
        if self.y < 0:
            raise DomainValidationError("y must be non-negative")

    def distance_to(self, other: Point) -> float:
        return hypot(self.x - other.x, self.y - other.y)
