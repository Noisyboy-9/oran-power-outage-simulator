import structlog

from simulator.controllers.base import RUController
from simulator.controllers.utils import (
    _is_selected_for_timestamp,
    _set_selected_status,
    _validate_timestamp,
)
from simulator.domain.ru import RU, RUStatus

logger = structlog.get_logger(__name__)


class ThresholdStaggeredActiveController(RUController):
    def __init__(self, threshold_percentage: float) -> None:
        if (
            isinstance(threshold_percentage, bool)
            or not isinstance(threshold_percentage, int | float)
            or not 0 <= threshold_percentage <= 100
        ):
            raise ValueError("threshold_percentage must be between 0 and 100")
        self.threshold_percentage = float(threshold_percentage)
        self._staggered_started = False

    def update(self, rus: list[RU], timestamp: int) -> list[RU]:
        _validate_timestamp(timestamp)
        if not rus:
            return rus

        if not self._staggered_started and all(
            ru.get_battery() / ru.get_initial_capacity() * 100
            <= self.threshold_percentage
            for ru in rus
        ):
            self._staggered_started = True

        for ru in rus:
            selected = not self._staggered_started or _is_selected_for_timestamp(
                ru, timestamp
            )
            if not selected:
                ru.set_status(RUStatus.SLEEP)
                continue

            _set_selected_status(
                ru,
                timestamp,
                type(self).__name__,
                logger,
            )

        return rus
