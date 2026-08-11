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


def test_unassociated_user_is_not_served() -> None:
    user = User(id=1)
    environment = FakeEnvironment([user], [make_ru(1, RUStatus.ACTIVE)])

    assert _served_user_fraction(environment) == 0.0


def test_active_associated_ru_serves_without_a_connection_graph_edge() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_associated_ru(user, ru)

    assert _served_user_fraction(environment) == 1.0


def test_sleeping_associated_ru_does_not_serve_a_user() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.SLEEP)
    environment = FakeEnvironment([user], [ru])
    environment.set_associated_ru(user, ru)

    assert _served_user_fraction(environment) == 0.0


def test_active_ru_with_depleted_battery_does_not_serve_a_user() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_associated_ru(user, ru)
    ru.update_battery(delta_time=10.0)

    assert _served_user_fraction(environment) == 0.0


def test_active_non_associated_ru_does_not_serve_a_user() -> None:
    user = User(id=1)
    associated_ru = make_ru(1, RUStatus.SLEEP)
    alternative_ru = make_ru(2, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [associated_ru, alternative_ru])
    environment.set_associated_ru(user, associated_ru)

    assert _served_user_fraction(environment) == 0.0


def test_unassociated_user_with_a_valid_edge_is_not_served() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.5)

    assert _served_user_fraction(environment) == 0.0
