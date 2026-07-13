from simulator.controllers.base import RUController
from simulator.controllers.utils import _set_selected_status, _validate_timestamp
from simulator.domain.ru import RU


class AlwaysActiveController(RUController):
    def update(self, rus: list[RU], timestamp: int) -> None:
        _validate_timestamp(timestamp)
        for ru in rus:
            _set_selected_status(ru, timestamp, type(self).__name__)
