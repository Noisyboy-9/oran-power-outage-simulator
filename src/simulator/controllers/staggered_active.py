import structlog

from simulator.controllers.base import RUController
from simulator.controllers.utils import (
    _is_selected_for_timestamp,
    _set_selected_status,
    _validate_timestamp,
)
from simulator.domain.ru import RU, RUStatus

logger = structlog.get_logger(__name__)


class StaggeredActiveController(RUController):
    def update(self, RUs: list[RU], timestamp: int) -> None:
        _validate_timestamp(timestamp)
        for ru in RUs:
            if not _is_selected_for_timestamp(ru, timestamp):
                ru.set_status(RUStatus.SLEEP)
                continue

            _set_selected_status(
                ru,
                timestamp,
                type(self).__name__,
                logger,
            )
