import pytest

from simulator.controllers.always_active import AlwaysActiveController
from simulator.controllers.base import RUController
from simulator.domain.ru import RU, RUStatus


def make_ru(
    *,
    id: int = 1,
    battery: float = 10.0,
    status: RUStatus = RUStatus.SLEEP,
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


def test_controller_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        RUController()


def test_activates_ru_with_more_than_required_battery() -> None:
    ru = make_ru(battery=3.0)

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.ACTIVE


def test_activates_ru_with_exactly_required_battery() -> None:
    ru = make_ru(battery=1.0)

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.ACTIVE


def test_activates_ru_with_exactly_the_zero_user_consumption() -> None:
    ru = make_ru(
        battery=1.0,
        zero_user_consumption=1.0,
        one_user_consumption=2.0,
    )

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.ACTIVE


def test_sleeps_ru_with_insufficient_battery() -> None:
    ru = make_ru(battery=0.5, status=RUStatus.ACTIVE)

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.SLEEP


def test_underpowered_ru_remains_asleep() -> None:
    ru = make_ru(battery=0.5, status=RUStatus.ACTIVE)

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.SLEEP


def test_returns_the_supplied_ru_list() -> None:
    rus = [make_ru()]

    result = AlwaysActiveController().update(rus, timestamp=0)

    assert result is rus


def test_empty_ru_list_is_a_no_op() -> None:
    rus: list[RU] = []

    result = AlwaysActiveController().update(rus, timestamp=0)

    assert result is rus


@pytest.mark.parametrize("timestamp", [-1, 1.5, True])
def test_rejects_invalid_timestamp(timestamp: object) -> None:
    with pytest.raises(ValueError, match="timestamp"):
        AlwaysActiveController().update([], timestamp)  # type: ignore[arg-type]
