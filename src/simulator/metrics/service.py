from simulator.environment import Environment


def _served_user_fraction(environment: Environment) -> float:
    users = environment.get_users()
    if not users:
        raise ValueError("cannot calculate served-user fraction without users")
    served_user_count = sum(
        environment.get_associated_ru(user) is not None for user in users
    )
    return served_user_count / len(users)
