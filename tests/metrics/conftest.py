import networkx as nx

from simulator.configuration import (
    ApplicationConfig,
    ControllerConfig,
    ControllerKind,
    LoggingConfig,
    MetricKind,
    MetricsConfig,
    SimulationConfig,
    TimestampConfig,
)
from simulator.domain import RU, RUStatus, User
from simulator.environment import EnvironmentConfig, MapConfig, RUConfig


def make_application_config() -> ApplicationConfig:
    return ApplicationConfig(
        environment=EnvironmentConfig(
            map=MapConfig(width=2, height=2),
            ru=RUConfig(
                count=1,
                initial_battery=10.0,
                initial_status=RUStatus.ACTIVE,
                zero_user_consumption=1.0,
                one_user_consumption=2.0,
                multi_user_consumption_per_user=1.5,
                sleep_consumption=0.5,
                user_capacity=100,
                coverage_radius=1.0,
            ),
            user_count=1,
            random_seed=7,
        ),
        controller=ControllerConfig(kind=ControllerKind.ALWAYS_ACTIVE),
        logging=LoggingConfig(
            logger_name="test",
            level=20,
            destination="stdout",
            format="json",
            include_logger_name=False,
            include_log_level=False,
            timestamp=TimestampConfig(key="logged_at", format="iso", utc=True),
            cache_loggers_on_first_use=False,
            propagate=False,
        ),
        simulation=SimulationConfig(
            steps=1,
            metrics=MetricsConfig(
                collectors=(MetricKind.AVERAGE_EMERGENCY_QOS,),
                minimum_emergency_service_fraction=0.5,
                minimum_service_link_weight=0.0,
            ),
        ),
    )


class FakeEnvironment:
    def __init__(self, users: list[User], rus: list[RU]) -> None:
        self._users = users
        self._rus = rus
        self._connection_weights: dict[tuple[User, RU], float] = {}
        self._associations: dict[User, RU | None] = {user: None for user in users}

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

    def get_associated_ru(self, user: User) -> RU | None:
        return self._associations.get(user)

    def set_associated_ru(self, user: User, ru: RU | None) -> None:
        self._associations[user] = ru


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
