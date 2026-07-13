import logging

from simulator.domain.ru import RU, RUStatus


def _validate_timestamp(timestamp: int) -> None:
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
        raise ValueError("timestamp must be a non-negative integer")


def _can_activate(ru: RU) -> bool:
    return ru.get_battery() >= ru.active_consumption


def _is_selected_for_timestamp(ru: RU, timestamp: int) -> bool:
    selected_id_parity = (timestamp // 10) % 2
    return ru.id % 2 == selected_id_parity


def _set_selected_status(
    ru: RU,
    timestamp: int,
    controller_name: str,
    logger: logging.Logger | None = None,
) -> None:
    if _can_activate(ru):
        ru.set_status(RUStatus.ACTIVE)
        return

    ru.set_status(RUStatus.SLEEP)
    if logger is not None:
        logger.info(
            "%s could not activate RU %s at timestamp %s: battery=%s, required=%s",
            controller_name,
            ru.id,
            timestamp,
            ru.get_battery(),
            ru.active_consumption,
        )
