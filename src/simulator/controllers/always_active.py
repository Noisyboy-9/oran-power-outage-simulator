from simulator.controllers.base import RUController
from simulator.controllers.utils import _set_selected_status, _validate_timestamp
from simulator.domain.ru import RU


class AlwaysActiveController(RUController):
    def update(self, RUs: list[RU], timestamp: int) -> None:
        _validate_timestamp(timestamp)
        for ru in RUs:
            _set_selected_status(ru, timestamp, type(self).__name__)
