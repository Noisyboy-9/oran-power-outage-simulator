import pytest

from simulator.domain.errors import DomainValidationError
from simulator.domain.ru import RU, RUStatus


def make_ru(**overrides: object) -> RU:
    values = {
        "id": 1,
        "battery": 10.0,
        "status": RUStatus.ACTIVE,
        "zero_user_consumption": 1.0,
        "one_user_consumption": 2.0,
        "multi_user_consumption_per_user": 1.5,
        "sleep_consumption": 0.5,
        "user_capacity": 100,
    }
    values.update(overrides)
    return RU(**values)


def test_status_has_sleep_and_active_states() -> None:
    assert {status.value for status in RUStatus} == {"sleep", "active"}


def test_exposes_battery_initial_capacity_and_user_capacity() -> None:
    ru = make_ru(battery=12.0, user_capacity=3)

    assert ru.get_battery() == 12.0
    assert ru.get_initial_capacity() == 12.0
    assert ru.user_capacity == 3
    assert not hasattr(ru, "battery")


def test_sets_and_gets_status() -> None:
    ru = make_ru(status=RUStatus.ACTIVE)

    result = ru.set_status(RUStatus.SLEEP)

    assert result is None
    assert ru.get_status() is RUStatus.SLEEP
    assert not hasattr(ru, "status")


def test_rejects_invalid_status_update() -> None:
    ru = make_ru()

    with pytest.raises(DomainValidationError, match="status"):
        ru.set_status("sleep")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("serviced_user_count", "expected_battery"),
    [(0, 9.0), (1, 8.0), (2, 7.0), (3, 5.5)],
)
def test_active_ru_consumption_depends_on_serviced_user_count(
    serviced_user_count: int, expected_battery: float
) -> None:
    ru = make_ru()

    result = ru.update_battery(serviced_user_count=serviced_user_count)

    assert result is None
    assert ru.get_battery() == pytest.approx(expected_battery)
    assert ru.get_initial_capacity() == 10.0


def test_sleeping_ru_uses_custom_timestep() -> None:
    ru = make_ru(status=RUStatus.SLEEP)

    ru.update_battery(delta_time=4.0)

    assert ru.get_battery() == pytest.approx(8.0)


def test_sleeping_ru_uses_sleep_consumption_regardless_of_serviced_users() -> None:
    ru = make_ru(status=RUStatus.SLEEP)

    ru.update_battery(serviced_user_count=3)

    assert ru.get_battery() == pytest.approx(9.5)


@pytest.mark.parametrize("serviced_user_count", [-1, True, 1.5])
def test_rejects_invalid_serviced_user_count(serviced_user_count: object) -> None:
    with pytest.raises(DomainValidationError, match="serviced_user_count"):
        make_ru().update_battery(serviced_user_count=serviced_user_count)  # type: ignore[arg-type]


def test_battery_is_clamped_at_zero() -> None:
    ru = make_ru(battery=1.0)

    ru.update_battery()

    assert ru.get_battery() == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 0),
        ("battery", 0.0),
        ("zero_user_consumption", 0.0),
        ("one_user_consumption", 0.0),
        ("multi_user_consumption_per_user", 0.0),
        ("sleep_consumption", 0.0),
        ("id", -1),
        ("battery", -1.0),
        ("zero_user_consumption", -1.0),
        ("one_user_consumption", -1.0),
        ("multi_user_consumption_per_user", -1.0),
        ("sleep_consumption", -1.0),
    ],
)
def test_rejects_non_positive_constructor_values(field: str, value: float) -> None:
    with pytest.raises(DomainValidationError, match=field):
        make_ru(**{field: value})


def test_rejects_invalid_constructor_status() -> None:
    with pytest.raises(DomainValidationError, match="status"):
        make_ru(status="active")


@pytest.mark.parametrize("user_capacity", [0, -1, 1.5, True, "100"])
def test_rejects_invalid_user_capacity(user_capacity: object) -> None:
    with pytest.raises(DomainValidationError, match="user_capacity"):
        make_ru(user_capacity=user_capacity)
