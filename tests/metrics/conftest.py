from simulator.domain import RU, RUStatus, User


class FakeEnvironment:
    def __init__(self, users: list[User], rus: list[RU]) -> None:
        self._users = users
        self._rus = rus
        self._connection_weights: dict[tuple[User, RU], float] = {}

    def get_users(self) -> list[User]:
        return self._users.copy()

    def get_rus(self) -> list[RU]:
        return self._rus.copy()

    def get_connection_weight(self, user: User, ru: RU) -> float:
        return self._connection_weights.get((user, ru), 0.0)

    def set_connection_weight(self, user: User, ru: RU, weight: float) -> None:
        self._connection_weights[(user, ru)] = weight


def make_ru(id: int, status: RUStatus) -> RU:
    return RU(
        id=id,
        battery=10.0,
        status=status,
        active_consumption=1.0,
        sleep_consumption=0.5,
    )
