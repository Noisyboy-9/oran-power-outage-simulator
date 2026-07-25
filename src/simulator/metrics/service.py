from simulator.domain import RUStatus
from simulator.environment import Environment


def _validate_minimum_service_link_weight(
    minimum_service_link_weight: float,
) -> None:
    if (
        isinstance(minimum_service_link_weight, bool)
        or not isinstance(minimum_service_link_weight, (int, float))
        or not 0 <= minimum_service_link_weight <= 1
    ):
        raise ValueError("minimum_service_link_weight must be a number between 0 and 1")


def _served_user_fraction(
    environment: Environment, minimum_service_link_weight: float
) -> float:
    _validate_minimum_service_link_weight(minimum_service_link_weight)
    users = environment.get_users()
    if not users:
        raise ValueError("cannot calculate served-user fraction without users")
    graph = environment.get_connectivity_graph()
    served_user_count = sum(
        any(
            graph.has_edge(user, ru)
            and ru.get_status() is RUStatus.ACTIVE
            and ru.get_battery() > 0
            and environment.get_connection_weight(user, ru)
            >= minimum_service_link_weight
            for ru in environment.get_rus()
        )
        for user in users
    )
    return served_user_count / len(users)
