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
        (associated_ru := environment.get_associated_ru(user)) is not None
        and graph.has_edge(user, associated_ru)
        and associated_ru.get_status() is RUStatus.ACTIVE
        and associated_ru.get_battery() > 0
        and environment.get_connection_weight(user, associated_ru)
            >= minimum_service_link_weight
        for user in users
    )
    return served_user_count / len(users)
