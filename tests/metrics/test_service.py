import pytest
from conftest import FakeEnvironment, make_ru

from simulator.domain import RUStatus, User
from simulator.metrics.service import _served_user_fraction


def test_empty_user_set_is_rejected() -> None:
    environment = FakeEnvironment([], [make_ru(1, RUStatus.ACTIVE)])

    with pytest.raises(
        ValueError, match="cannot calculate served-user fraction without users"
    ):
        _served_user_fraction(environment)


def test_no_active_connection_serves_no_users() -> None:
    user = User(id=1)
    environment = FakeEnvironment([user], [make_ru(1, RUStatus.ACTIVE)])

    assert _served_user_fraction(environment) == 0.0


def test_active_connected_ru_serves_a_user() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.5)

    assert _served_user_fraction(environment) == 1.0


def test_sleeping_connected_ru_does_not_serve_a_user() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.SLEEP)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.5)

    assert _served_user_fraction(environment) == 0.0


def test_multiple_active_connections_count_a_user_once() -> None:
    user = User(id=1)
    first_ru = make_ru(1, RUStatus.ACTIVE)
    second_ru = make_ru(2, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [first_ru, second_ru])
    environment.set_connection_weight(user, first_ru, 0.5)
    environment.set_connection_weight(user, second_ru, 0.75)

    assert _served_user_fraction(environment) == 1.0
