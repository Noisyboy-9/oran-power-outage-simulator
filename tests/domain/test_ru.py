import pytest

from simulator.domain.errors import DomainValidationError
from simulator.domain.ru import RU, RUStatus


def make_ru(**overrides: object) -> RU:
    values = {
        "id": 1,
        "battery": 10.0,
        "status": RUStatus.ACTIVE,
        "active_consumption": 2.0,
        "sleep_consumption": 0.5,
    }
    values.update(overrides)
    return RU(**values)


def test_status_has_sleep_and_active_states() -> None:
    assert {status.value for status in RUStatus} == {"sleep", "active"}


def test_active_ru_uses_default_timestep() -> None:
    ru = make_ru()

    result = ru.update_battery()

    assert result is None
    assert ru.battery == pytest.approx(8.0)


def test_sleeping_ru_uses_custom_timestep() -> None:
    ru = make_ru(status=RUStatus.SLEEP)

    ru.update_battery(delta_time=4.0)

    assert ru.battery == pytest.approx(8.0)


def test_battery_is_clamped_at_zero() -> None:
    ru = make_ru(battery=1.0)

    ru.update_battery()

    assert ru.battery == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 0),
        ("battery", 0.0),
        ("active_consumption", 0.0),
        ("sleep_consumption", 0.0),
        ("id", -1),
        ("battery", -1.0),
        ("active_consumption", -1.0),
        ("sleep_consumption", -1.0),
    ],
)
def test_rejects_non_positive_constructor_values(field: str, value: float) -> None:
    with pytest.raises(DomainValidationError, match=field):
        make_ru(**{field: value})
