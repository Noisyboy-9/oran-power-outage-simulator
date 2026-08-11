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
        zero_user_consumption: float,
        one_user_consumption: float,
        multi_user_consumption_per_user: float,
        sleep_consumption: float,
        user_capacity: int,
    ) -> None:
        positive_fields = {
            "id": id,
            "battery": battery,
            "zero_user_consumption": zero_user_consumption,
            "one_user_consumption": one_user_consumption,
            "multi_user_consumption_per_user": multi_user_consumption_per_user,
            "sleep_consumption": sleep_consumption,
        }
        for field, value in positive_fields.items():
            if value <= 0:
                raise DomainValidationError(f"{field} must be positive")
        if not isinstance(status, RUStatus):
            raise DomainValidationError("status must be an RUStatus")
        if (
            isinstance(user_capacity, bool)
            or not isinstance(user_capacity, int)
            or user_capacity <= 0
        ):
            raise DomainValidationError("user_capacity must be a positive integer")

        self.id = id
        self.zero_user_consumption = zero_user_consumption
        self.one_user_consumption = one_user_consumption
        self.multi_user_consumption_per_user = multi_user_consumption_per_user
        self.sleep_consumption = sleep_consumption
        self.user_capacity = user_capacity
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

    def update_battery(
        self, delta_time: float = 1.0, serviced_user_count: int = 0
    ) -> None:
        if (
            isinstance(serviced_user_count, bool)
            or not isinstance(serviced_user_count, int)
            or serviced_user_count < 0
        ):
            raise DomainValidationError(
                "serviced_user_count must be a non-negative integer"
            )

        if self._status is RUStatus.SLEEP:
            consumption = self.sleep_consumption
        elif serviced_user_count == 0:
            consumption = self.zero_user_consumption
        elif serviced_user_count == 1:
            consumption = self.one_user_consumption
        else:
            consumption = serviced_user_count * self.multi_user_consumption_per_user
        self._battery = max(0.0, self._battery - delta_time * consumption)
