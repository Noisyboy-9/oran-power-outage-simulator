import pytest

from simulator.controllers.threshold_staggered_active import (
    ThresholdStaggeredActiveController,
)
from simulator.domain.ru import RU, RUStatus


def make_ru(
    id: int,
    *,
    battery: float = 10.0,
    status: RUStatus = RUStatus.SLEEP,
    active_consumption: float = 1.0,
) -> RU:
    return RU(
        id=id,
        battery=battery,
        status=status,
        active_consumption=active_consumption,
        sleep_consumption=0.5,
    )


def drain_to(ru: RU, target_battery: float) -> None:
    ru.set_status(RUStatus.ACTIVE)
    delta_time = (ru.get_battery() - target_battery) / ru.active_consumption
    ru.update_battery(delta_time=delta_time)


@pytest.mark.parametrize("threshold", [-0.1, 100.1, "50", True])
def test_rejects_invalid_threshold(threshold: object) -> None:
    with pytest.raises(ValueError, match="threshold_percentage"):
        ThresholdStaggeredActiveController(threshold)  # type: ignore[arg-type]


def test_returns_the_supplied_ru_list() -> None:
    rus = [make_ru(1)]

    result = ThresholdStaggeredActiveController(50.0).update(rus, timestamp=0)

    assert result is rus


def test_keeps_every_ru_active_before_all_reach_threshold() -> None:
    odd_ru = make_ru(1)
    even_ru = make_ru(2)
    drain_to(odd_ru, 5.0)
    drain_to(even_ru, 6.0)

    controller = ThresholdStaggeredActiveController(50.0)

    controller.update([odd_ru, even_ru], timestamp=0)

    assert odd_ru.get_status() is RUStatus.ACTIVE
    assert even_ru.get_status() is RUStatus.ACTIVE


def test_threshold_equality_for_every_ru_starts_staggering() -> None:
    odd_ru = make_ru(1)
    even_ru = make_ru(2)
    drain_to(odd_ru, 5.0)
    drain_to(even_ru, 5.0)

    controller = ThresholdStaggeredActiveController(50.0)

    controller.update([odd_ru, even_ru], timestamp=0)

    assert odd_ru.get_status() is RUStatus.SLEEP
    assert even_ru.get_status() is RUStatus.ACTIVE


def test_transition_uses_global_timestamp_without_restart() -> None:
    odd_ru = make_ru(1)
    even_ru = make_ru(2)
    drain_to(odd_ru, 5.0)
    drain_to(even_ru, 5.0)

    controller = ThresholdStaggeredActiveController(50.0)

    controller.update([odd_ru, even_ru], timestamp=37)

    assert odd_ru.get_status() is RUStatus.ACTIVE
    assert even_ru.get_status() is RUStatus.SLEEP


def test_transition_remains_permanent_for_later_ru_collection() -> None:
    controller = ThresholdStaggeredActiveController(50.0)
    first_odd = make_ru(1)
    first_even = make_ru(2)
    drain_to(first_odd, 5.0)
    drain_to(first_even, 5.0)
    controller.update([first_odd, first_even], timestamp=0)
    replacement_odd = make_ru(1)
    replacement_even = make_ru(2)

    controller.update([replacement_odd, replacement_even], timestamp=10)

    assert replacement_odd.get_status() is RUStatus.ACTIVE
    assert replacement_even.get_status() is RUStatus.SLEEP


def test_empty_list_does_not_start_transition() -> None:
    controller = ThresholdStaggeredActiveController(50.0)
    rus: list[RU] = []

    result = controller.update(rus, timestamp=0)

    assert result is rus
    odd_ru = make_ru(1)
    even_ru = make_ru(2)

    controller.update([odd_ru, even_ru], timestamp=10)

    assert odd_ru.get_status() is RUStatus.ACTIVE
    assert even_ru.get_status() is RUStatus.ACTIVE


def test_underpowered_ru_sleeps_before_transition() -> None:
    ru = make_ru(1, battery=1.0, active_consumption=2.0)

    ThresholdStaggeredActiveController(0.0).update([ru], timestamp=3)

    assert ru.get_status() is RUStatus.SLEEP


def test_selected_underpowered_ru_sleeps_after_transition() -> None:
    ru = make_ru(2, battery=1.0, active_consumption=2.0)

    ThresholdStaggeredActiveController(100.0).update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP


def test_rejects_invalid_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        ThresholdStaggeredActiveController(50.0).update([], timestamp=-1)
