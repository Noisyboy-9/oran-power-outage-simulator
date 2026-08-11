import pytest
from structlog.testing import capture_logs

from simulator.controllers.staggered_active import StaggeredActiveController
from simulator.domain.ru import RU, RUStatus


def make_ru(
    id: int,
    *,
    battery: float = 10.0,
    status: RUStatus = RUStatus.ACTIVE,
    zero_user_consumption: float = 1.0,
    one_user_consumption: float = 2.0,
    multi_user_consumption_per_user: float = 1.5,
) -> RU:
    return RU(
        id=id,
        battery=battery,
        status=status,
        zero_user_consumption=zero_user_consumption,
        one_user_consumption=one_user_consumption,
        multi_user_consumption_per_user=multi_user_consumption_per_user,
        sleep_consumption=0.5,
        user_capacity=100,
    )


@pytest.mark.parametrize(
    ("timestamp", "active_id", "sleeping_id"),
    [
        (9, 2, 1),
        (10, 1, 2),
        (19, 1, 2),
        (20, 2, 1),
    ],
)
def test_selects_group_at_timestamp_boundaries(
    timestamp: int, active_id: int, sleeping_id: int
) -> None:
    rus = [make_ru(1), make_ru(2)]

    StaggeredActiveController().update(rus, timestamp)

    statuses = {ru.id: ru.get_status() for ru in rus}
    assert statuses[active_id] is RUStatus.ACTIVE
    assert statuses[sleeping_id] is RUStatus.SLEEP


def test_selected_ru_with_exact_battery_is_active() -> None:
    ru = make_ru(2, battery=1.0, status=RUStatus.SLEEP)

    StaggeredActiveController().update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.ACTIVE


def test_selected_underpowered_ru_sleeps() -> None:
    ru = make_ru(2, battery=0.5)

    StaggeredActiveController().update([ru], timestamp=7)

    assert ru.get_status() is RUStatus.SLEEP


def test_non_selected_ru_sleeps() -> None:
    ru = make_ru(1, battery=0.5)

    StaggeredActiveController().update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP


def test_logs_zero_user_consumption_when_selected_ru_cannot_activate() -> None:
    ru = make_ru(2, battery=0.5, zero_user_consumption=1.0)

    with capture_logs() as logs:
        StaggeredActiveController().update([ru], timestamp=0)

    activation_events = [
        event for event in logs if event["event"] == "ru_activation_failed"
    ]
    assert len(activation_events) == 1
    assert activation_events[0]["log_level"] == "info"
    assert activation_events[0]["required_battery"] == 1.0


def test_returns_the_supplied_ru_list() -> None:
    rus = [make_ru(1)]

    result = StaggeredActiveController().update(rus, timestamp=0)

    assert result is rus


def test_empty_ru_list_is_a_no_op() -> None:
    rus: list[RU] = []

    result = StaggeredActiveController().update(rus, timestamp=0)

    assert result is rus


def test_rejects_invalid_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        StaggeredActiveController().update([], timestamp=-1)
