import pytest
from conftest import FakeEnvironment, make_ru

from simulator.domain import RUStatus, User
from simulator.metrics.service import _served_user_fraction


def test_empty_user_set_is_rejected() -> None:
    environment = FakeEnvironment([], [make_ru(1, RUStatus.ACTIVE)])

    with pytest.raises(
        ValueError, match="cannot calculate served-user fraction without users"
    ):
        _served_user_fraction(environment, 0.0)


def test_no_active_connection_serves_no_users() -> None:
    user = User(id=1)
    environment = FakeEnvironment([user], [make_ru(1, RUStatus.ACTIVE)])

    assert _served_user_fraction(environment, 0.0) == 0.0


def test_active_connected_ru_serves_a_user() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.5)
    environment.set_associated_ru(user, ru)

    assert _served_user_fraction(environment, 0.0) == 1.0


def test_sleeping_connected_ru_does_not_serve_a_user() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.SLEEP)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.5)
    environment.set_associated_ru(user, ru)

    assert _served_user_fraction(environment, 0.0) == 0.0


def test_multiple_active_connections_count_a_user_once() -> None:
    user = User(id=1)
    first_ru = make_ru(1, RUStatus.ACTIVE)
    second_ru = make_ru(2, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [first_ru, second_ru])
    environment.set_connection_weight(user, first_ru, 0.5)
    environment.set_connection_weight(user, second_ru, 0.75)
    environment.set_associated_ru(user, first_ru)

    assert _served_user_fraction(environment, 0.0) == 1.0


def test_rejects_edge_below_service_link_threshold() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.29)
    environment.set_associated_ru(user, ru)

    assert _served_user_fraction(environment, 0.3) == 0.0


def test_accepts_edge_equal_to_service_link_threshold() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.3)
    environment.set_associated_ru(user, ru)

    assert _served_user_fraction(environment, 0.3) == 1.0


def test_zero_threshold_does_not_accept_an_absent_edge() -> None:
    user = User(id=1)
    environment = FakeEnvironment([user], [make_ru(1, RUStatus.ACTIVE)])

    assert _served_user_fraction(environment, 0.0) == 0.0


def test_active_ru_with_depleted_battery_does_not_serve_a_user() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.5)
    environment.set_associated_ru(user, ru)
    ru.update_battery(delta_time=10.0)

    assert _served_user_fraction(environment, 0.3) == 0.0


def test_qualifying_non_associated_ru_does_not_serve_a_user() -> None:
    user = User(id=1)
    associated_ru = make_ru(1, RUStatus.SLEEP)
    alternative_ru = make_ru(2, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [associated_ru, alternative_ru])
    environment.set_connection_weight(user, associated_ru, 0.8)
    environment.set_connection_weight(user, alternative_ru, 0.9)
    environment.set_associated_ru(user, associated_ru)

    assert _served_user_fraction(environment, 0.6) == 0.0


def test_unassociated_user_with_a_valid_edge_is_not_served() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.5)

    assert _served_user_fraction(environment, 0.3) == 0.0


@pytest.mark.parametrize("minimum_service_link_weight", [-0.1, 1.1, True, "0.3"])
def test_rejects_invalid_service_link_threshold(
    minimum_service_link_weight: object,
) -> None:
    environment = FakeEnvironment([User(id=1)], [make_ru(1, RUStatus.ACTIVE)])

    with pytest.raises(ValueError, match="minimum_service_link_weight"):
        _served_user_fraction(environment, minimum_service_link_weight)
