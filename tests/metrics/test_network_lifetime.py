import math

import pytest
from conftest import FakeEnvironment, make_ru

from simulator.domain import RUStatus, User
from simulator.metrics.network_lifetime import NetworkLifetimeCollector


def make_environment(served_user_count: int) -> FakeEnvironment:
    users = [User(id=1), User(id=2)]
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment(users, [ru])
    for user in users[:served_user_count]:
        environment.set_connection_weight(user, ru, 0.5)
    return environment


def test_network_lifetime_stops_at_the_observation_before_first_violation() -> None:
    collector = NetworkLifetimeCollector(minimum_emergency_service_fraction=0.5)
    environment_serving_all_users = make_environment(2)
    environment_serving_exactly_half_of_users = make_environment(1)
    environment_serving_no_users = make_environment(0)

    collector.collect(environment_serving_all_users, 0)
    collector.collect(environment_serving_exactly_half_of_users, 1)
    collector.collect(environment_serving_no_users, 2)

    assert collector.name == "network_lifetime"
    assert collector.finish_calculation() == 1.0


def test_network_lifetime_does_not_extend_after_a_recovery() -> None:
    collector = NetworkLifetimeCollector(minimum_emergency_service_fraction=0.5)

    collector.collect(make_environment(2), 0)
    collector.collect(make_environment(1), 1)
    collector.collect(make_environment(0), 2)
    collector.collect(make_environment(2), 3)

    assert collector.finish_calculation() == 1.0


def test_network_lifetime_returns_zero_for_an_initial_violation() -> None:
    collector = NetworkLifetimeCollector(minimum_emergency_service_fraction=0.5)

    collector.collect(make_environment(0), 0)

    assert collector.finish_calculation() == 0.0


def test_network_lifetime_collection_does_not_mutate_environment() -> None:
    environment = make_environment(1)
    before_batteries = [ru.get_battery() for ru in environment.get_rus()]
    before_statuses = [ru.get_status() for ru in environment.get_rus()]
    before_connections = environment._connection_weights.copy()

    NetworkLifetimeCollector(minimum_emergency_service_fraction=0.5).collect(
        environment, 0
    )

    assert [ru.get_battery() for ru in environment.get_rus()] == before_batteries
    assert [ru.get_status() for ru in environment.get_rus()] == before_statuses
    assert environment._connection_weights == before_connections


def test_network_lifetime_is_infinite_when_sla_is_never_violated() -> None:
    collector = NetworkLifetimeCollector(minimum_emergency_service_fraction=0.5)

    collector.collect(make_environment(1), 0)
    collector.collect(make_environment(2), 1)

    assert math.isinf(collector.finish_calculation())


@pytest.mark.parametrize("minimum_emergency_service_fraction", [0, 1.1, True, "0.5"])
def test_network_lifetime_rejects_invalid_service_fraction(
    minimum_emergency_service_fraction: float,
) -> None:
    with pytest.raises(ValueError, match="minimum_emergency_service_fraction"):
        NetworkLifetimeCollector(minimum_emergency_service_fraction)
