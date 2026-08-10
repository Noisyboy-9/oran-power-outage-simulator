import networkx as nx

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

    def get_connectivity_graph(self) -> nx.Graph:
        graph = nx.Graph()
        graph.add_nodes_from([*self._users, *self._rus])
        graph.add_weighted_edges_from(
            (user, ru, weight)
            for (user, ru), weight in self._connection_weights.items()
        )
        return graph

    def get_connection_weight(self, user: User, ru: RU) -> float:
        return self._connection_weights.get((user, ru), 0.0)

    def set_connection_weight(self, user: User, ru: RU, weight: float) -> None:
        self._connection_weights[(user, ru)] = weight


def make_ru(id: int, status: RUStatus) -> RU:
    return RU(
        id=id,
        battery=10.0,
        status=status,
        zero_user_consumption=1.0,
        one_user_consumption=2.0,
        multi_user_consumption_per_user=1.5,
        sleep_consumption=0.5,
        user_capacity=100,
    )
