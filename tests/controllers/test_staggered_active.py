import pytest

from simulator.controllers.staggered_active import StaggeredActiveController
from simulator.domain.ru import RU, RUStatus


def make_ru(
    id: int,
    *,
    battery: float = 10.0,
    status: RUStatus = RUStatus.ACTIVE,
    active_consumption: float = 2.0,
) -> RU:
    return RU(
        id=id,
        battery=battery,
        status=status,
        active_consumption=active_consumption,
        sleep_consumption=0.5,
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
    ru = make_ru(2, battery=2.0, status=RUStatus.SLEEP)

    StaggeredActiveController().update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.ACTIVE


def test_selected_underpowered_ru_sleeps() -> None:
    ru = make_ru(2, battery=1.0)

    StaggeredActiveController().update([ru], timestamp=7)

    assert ru.get_status() is RUStatus.SLEEP


def test_non_selected_ru_sleeps() -> None:
    ru = make_ru(1, battery=1.0)

    StaggeredActiveController().update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP


def test_empty_ru_list_is_a_no_op() -> None:
    result = StaggeredActiveController().update([], timestamp=0)

    assert result is None


def test_rejects_invalid_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        StaggeredActiveController().update([], timestamp=-1)
