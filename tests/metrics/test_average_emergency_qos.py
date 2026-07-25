from conftest import FakeEnvironment, make_ru

from simulator.domain import RUStatus, User
from simulator.metrics.average_emergency_qos import AverageEmergencyQoSCollector


def make_environment(served_user_count: int) -> FakeEnvironment:
    users = [User(id=1), User(id=2)]
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment(users, [ru])
    for user in users[:served_user_count]:
        environment.set_connection_weight(user, ru, 0.5)
    return environment


def test_average_emergency_qos_records_zero_complete_and_partial_service() -> None:
    collector = AverageEmergencyQoSCollector()

    collector.collect(make_environment(0), 0)
    collector.collect(make_environment(2), 1)
    collector.collect(make_environment(1), 2)

    assert collector.name == "average_emergency_qos"
    assert collector.finish_calculation() == 0.5


def test_average_emergency_qos_counts_duplicate_active_coverage_once() -> None:
    user = User(id=1)
    first_ru = make_ru(1, RUStatus.ACTIVE)
    second_ru = make_ru(2, RUStatus.ACTIVE)
    environment_with_one_user_and_two_active_connections = FakeEnvironment(
        [user], [first_ru, second_ru]
    )
    environment_with_one_user_and_two_active_connections.set_connection_weight(
        user, first_ru, 0.5
    )
    environment_with_one_user_and_two_active_connections.set_connection_weight(
        user, second_ru, 0.75
    )
    collector = AverageEmergencyQoSCollector()

    collector.collect(environment_with_one_user_and_two_active_connections, 0)

    assert collector.finish_calculation() == 1.0


def test_average_emergency_qos_collection_does_not_mutate_environment() -> None:
    user = User(id=1)
    ru = make_ru(1, RUStatus.ACTIVE)
    environment = FakeEnvironment([user], [ru])
    environment.set_connection_weight(user, ru, 0.5)
    before_batteries = [candidate.get_battery() for candidate in environment.get_rus()]
    before_statuses = [candidate.get_status() for candidate in environment.get_rus()]
    before_connections = environment._connection_weights.copy()

    AverageEmergencyQoSCollector().collect(environment, 0)

    assert [
        candidate.get_battery() for candidate in environment.get_rus()
    ] == before_batteries
    assert [
        candidate.get_status() for candidate in environment.get_rus()
    ] == before_statuses
    assert environment._connection_weights == before_connections
