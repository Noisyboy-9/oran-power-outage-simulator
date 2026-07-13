from enum import Enum

from simulator.domain.errors import DomainValidationError


class RUStatus(Enum):
    SLEEP = "sleep"
    ACTIVE = "active"


class RU:
    def __init__(
        self,
        id: int,
        battery: float,
        status: RUStatus,
        active_consumption: float,
        sleep_consumption: float,
    ) -> None:
        positive_fields = {
            "id": id,
            "battery": battery,
            "active_consumption": active_consumption,
            "sleep_consumption": sleep_consumption,
        }
        for field, value in positive_fields.items():
            if value <= 0:
                raise DomainValidationError(f"{field} must be positive")
        if not isinstance(status, RUStatus):
            raise DomainValidationError("status must be an RUStatus")

        self.id = id
        self.active_consumption = active_consumption
        self.sleep_consumption = sleep_consumption
        self._battery = battery
        self._initial_capacity = battery
        self._status = status

    def get_battery(self) -> float:
        return self._battery

    def get_initial_capacity(self) -> float:
        return self._initial_capacity

    def get_status(self) -> RUStatus:
        return self._status

    def set_status(self, status: RUStatus) -> None:
        if not isinstance(status, RUStatus):
            raise DomainValidationError("status must be an RUStatus")
        self._status = status

    def update_battery(self, delta_time: float = 1.0) -> None:
        consumption = (
            self.active_consumption
            if self._status is RUStatus.ACTIVE
            else self.sleep_consumption
        )
        self._battery = max(0.0, self._battery - delta_time * consumption)
