import networkx as nx
import pytest

from simulator.domain.ru import RU, RUStatus
from simulator.domain.user import User
from simulator.environment import (
    Environment,
    EnvironmentConfig,
    MapConfig,
    RUConfig,
)


def make_environment(
    *,
    width: int = 2,
    height: int = 1,
    ru_count: int = 1,
    user_count: int = 1,
    coverage_radius: float = 2.0,
    random_seed: int = 7,
) -> Environment:
    return Environment(
        EnvironmentConfig(
            map=MapConfig(width=width, height=height),
            ru=RUConfig(
                count=ru_count,
                initial_battery=100.0,
                initial_status=RUStatus.ACTIVE,
                active_consumption=2.0,
                sleep_consumption=0.5,
                coverage_radius=coverage_radius,
            ),
            user_count=user_count,
            random_seed=random_seed,
        )
    )


def edge_weights_by_ids(environment: Environment) -> dict[tuple[int, int], float]:
    graph = environment.get_connectivity_graph()
    return {
        (ru.id, user.id): graph[ru][user]["weight"]
        for ru in environment.get_rus()
        for user in environment.get_users()
        if graph.has_edge(ru, user)
    }


def test_builds_undirected_bipartite_graph() -> None:
    environment = make_environment()
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]

    graph = environment.get_connectivity_graph()
    assert isinstance(graph, nx.Graph)
    assert not graph.is_directed()
    assert set(graph.nodes) == {ru, user}
    assert graph.nodes[ru]["bipartite"] == 0
    assert graph.nodes[user]["bipartite"] == 1
    assert graph.has_edge(ru, user)
    assert graph[ru][user]["weight"] == graph[user][ru]["weight"]


@pytest.mark.parametrize("coverage_radius", [1.0, 0.5])
def test_excludes_pairs_at_or_beyond_coverage_radius(
    coverage_radius: float,
) -> None:
    environment = make_environment(coverage_radius=coverage_radius)
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]

    graph = environment.get_connectivity_graph()
    assert set(graph.nodes) == {ru, user}
    assert graph.number_of_edges() == 0
    assert environment.get_connection_weight(user, ru) == 0.0


def test_connected_weight_is_positive_and_bounded_by_closeness() -> None:
    environment = make_environment(coverage_radius=2.0)
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]
    distance = environment.get_ru_locations()[ru].distance_to(
        environment.get_user_locations()[user]
    )
    closeness = 1 - distance / 2.0

    weight = environment.get_connection_weight(user, ru)

    assert 0.0 < weight <= closeness


def test_graph_contains_only_ru_to_user_edges() -> None:
    environment = make_environment(
        width=3,
        height=2,
        ru_count=2,
        user_count=2,
        coverage_radius=10.0,
    )

    for left, right in environment.get_connectivity_graph().edges:
        assert {type(left), type(right)} == {RU, User}


def test_equal_seeds_reproduce_connection_weights() -> None:
    first = make_environment(
        width=3,
        height=2,
        ru_count=2,
        user_count=2,
        coverage_radius=10.0,
        random_seed=19,
    )
    second = make_environment(
        width=3,
        height=2,
        ru_count=2,
        user_count=2,
        coverage_radius=10.0,
        random_seed=19,
    )

    assert edge_weights_by_ids(first) == edge_weights_by_ids(second)


def test_graph_getter_returns_independent_graph_copy() -> None:
    environment = make_environment()
    returned_graph = environment.get_connectivity_graph()
    returned_graph.clear()

    internal_copy = environment.get_connectivity_graph()
    assert internal_copy.number_of_nodes() == 2
    assert internal_copy.number_of_edges() == 1


def test_foreign_entities_have_no_connection() -> None:
    environment = make_environment()
    owned_ru = environment.get_rus()[0]
    owned_user = environment.get_users()[0]
    foreign_user_with_same_id = User(id=owned_user.id)
    foreign_ru_with_same_id = RU(
        id=owned_ru.id,
        battery=100.0,
        status=RUStatus.ACTIVE,
        active_consumption=2.0,
        sleep_consumption=0.5,
    )

    assert environment.get_connection_weight(foreign_user_with_same_id, owned_ru) == 0.0
    assert environment.get_connection_weight(owned_user, foreign_ru_with_same_id) == 0.0
