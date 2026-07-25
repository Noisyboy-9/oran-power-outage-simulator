from simulator.domain import RUStatus
from simulator.environment import Environment


def _served_user_fraction(environment: Environment) -> float:
    users = environment.get_users()
    served_user_count = sum(
        any(
            ru.get_status() is RUStatus.ACTIVE
            and environment.get_connection_weight(user, ru) > 0.0
            for ru in environment.get_rus()
        )
        for user in users
    )
    return served_user_count / len(users)
