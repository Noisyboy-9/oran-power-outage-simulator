from dataclasses import dataclass
from enum import Enum

from simulator.domain.errors import DomainValidationError


class RUStatus(Enum):
    SLEEP = "sleep"
    ACTIVE = "active"


@dataclass
class RU:
    id: int
    battery: float
    status: RUStatus
    active_consumption: float
    sleep_consumption: float

    def __post_init__(self) -> None:
        positive_fields = {
            "id": self.id,
            "battery": self.battery,
            "active_consumption": self.active_consumption,
            "sleep_consumption": self.sleep_consumption,
        }
        for field, value in positive_fields.items():
            if value <= 0:
                raise DomainValidationError(f"{field} must be positive")

    def update_battery(self, delta_time: float = 1.0) -> None:
        consumption = (
            self.active_consumption
            if self.status is RUStatus.ACTIVE
            else self.sleep_consumption
        )
        self.battery = max(0.0, self.battery - delta_time * consumption)
