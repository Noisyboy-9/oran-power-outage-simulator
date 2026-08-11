from simulator.domain import RUStatus
from simulator.environment import Environment


def _served_user_fraction(environment: Environment) -> float:
    users = environment.get_users()
    if not users:
        raise ValueError("cannot calculate served-user fraction without users")
    served_user_count = sum(
        (associated_ru := environment.get_associated_ru(user)) is not None
        and associated_ru.get_status() is RUStatus.ACTIVE
        and associated_ru.get_battery() > 0
        for user in users
    )
    return served_user_count / len(users)
