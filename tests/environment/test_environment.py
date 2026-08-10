import networkx as nx
import pytest

from simulator.controllers import AlwaysActiveController, RUController
from simulator.domain.errors import DomainValidationError
from simulator.domain.ru import RU, RUStatus
from simulator.domain.user import User
from simulator.environment import (
    Environment,
    EnvironmentConfig,
    MapConfig,
    RUConfig,
)


class RecordingController(RUController):
    def __init__(self) -> None:
        self.received_rus: list[RU] | None = None
        self.received_timestamp: int | None = None

    def update(self, rus: list[RU], timestamp: int) -> list[RU]:
        self.received_rus = rus
        self.received_timestamp = timestamp
        return rus


def make_config(
    *,
    width: int = 4,
    height: int = 3,
    ru_count: int = 2,
    user_count: int = 3,
    initial_battery: float = 100.0,
    initial_status: RUStatus = RUStatus.ACTIVE,
    zero_user_consumption: float = 2.0,
    one_user_consumption: float = 2.0,
    multi_user_consumption_per_user: float = 1.5,
    sleep_consumption: float = 0.5,
    user_capacity: int = 100,
    coverage_radius: float = 4.0,
    random_seed: int | None = 7,
) -> EnvironmentConfig:
    return EnvironmentConfig(
        map=MapConfig(width=width, height=height),
        ru=RUConfig(
            count=ru_count,
            initial_battery=initial_battery,
            initial_status=initial_status,
            zero_user_consumption=zero_user_consumption,
            one_user_consumption=one_user_consumption,
            multi_user_consumption_per_user=multi_user_consumption_per_user,
            sleep_consumption=sleep_consumption,
            user_capacity=user_capacity,
            coverage_radius=coverage_radius,
        ),
        user_count=user_count,
        random_seed=random_seed,
    )


def placement_signature(environment: Environment) -> tuple[tuple[int, int, int], ...]:
    ru_locations = sorted(
        ((ru.id, cell.x, cell.y) for ru, cell in environment.get_ru_locations().items())
    )
    user_locations = sorted(
        (
            (user.id, cell.x, cell.y)
            for user, cell in environment.get_user_locations().items()
        )
    )
    return tuple(ru_locations + user_locations)


def replace_connectivity_graph(
    environment: Environment,
    weighted_edges: list[tuple[RU, User, float]],
) -> None:
    controlled_graph = nx.Graph()
    controlled_graph.add_nodes_from([*environment.get_rus(), *environment.get_users()])
    controlled_graph.add_weighted_edges_from(weighted_edges)
    environment._connectivity_graph = controlled_graph


def rebuild_associations(
    environment: Environment,
    weighted_edges: list[tuple[RU, User, float]],
    minimum_service_link_weight: float,
) -> None:
    replace_connectivity_graph(environment, weighted_edges)
    environment._update_associations(minimum_service_link_weight)


def test_creates_row_major_map() -> None:
    environment = Environment(
        make_config(width=4, height=3), AlwaysActiveController(), 0.0
    )

    environment_map = environment.get_map()
    assert len(environment_map) == 3
    assert all(len(row) == 4 for row in environment_map)
    for y, row in enumerate(environment_map):
        for x, cell in enumerate(row):
            assert (cell.x, cell.y) == (x, y)


def test_creates_uniform_rus_and_sequential_entity_ids() -> None:
    environment = Environment(
        make_config(
            ru_count=2,
            user_count=3,
            initial_battery=80.0,
            initial_status=RUStatus.SLEEP,
            zero_user_consumption=3.0,
            one_user_consumption=2.0,
            multi_user_consumption_per_user=1.5,
            sleep_consumption=0.25,
        ),
        AlwaysActiveController(),
        0.0,
    )

    rus = environment.get_rus()
    users = environment.get_users()
    assert [ru.id for ru in rus] == [1, 2]
    assert [user.id for user in users] == [1, 2, 3]
    for ru in rus:
        assert ru.get_battery() == 80.0
        assert ru.get_initial_capacity() == 80.0
        assert ru.get_status() is RUStatus.SLEEP
        assert ru.zero_user_consumption == 3.0
        assert ru.one_user_consumption == 2.0
        assert ru.multi_user_consumption_per_user == 1.5
        assert ru.sleep_consumption == 0.25


def test_places_every_entity_in_one_distinct_cell() -> None:
    environment = Environment(make_config(), AlwaysActiveController(), 0.0)

    occupied_cells = [
        cell
        for row in environment.get_map()
        for cell in row
        if cell.occupant is not None
    ]
    assert len(occupied_cells) == 5
    assert len({(cell.x, cell.y) for cell in occupied_cells}) == 5

    environment_map = environment.get_map()
    for ru, cell in environment.get_ru_locations().items():
        assert cell.occupant is ru
        assert environment_map[cell.y][cell.x] is cell
    for user, cell in environment.get_user_locations().items():
        assert cell.occupant is user
        assert environment_map[cell.y][cell.x] is cell


def test_equal_seeds_reproduce_placements() -> None:
    first = Environment(make_config(random_seed=19), AlwaysActiveController(), 0.0)
    second = Environment(make_config(random_seed=19), AlwaysActiveController(), 0.0)

    assert placement_signature(first) == placement_signature(second)


def test_collection_getters_protect_environment_structure() -> None:
    environment = Environment(make_config(), AlwaysActiveController(), 0.0)

    returned_map = environment.get_map()
    returned_map[0].clear()
    returned_rus = environment.get_rus()
    returned_rus.clear()
    returned_users = environment.get_users()
    returned_users.clear()
    returned_ru_locations = environment.get_ru_locations()
    returned_ru_locations.clear()
    returned_user_locations = environment.get_user_locations()
    returned_user_locations.clear()

    assert len(environment.get_map()[0]) == 4
    assert len(environment.get_rus()) == 2
    assert len(environment.get_users()) == 3
    assert len(environment.get_ru_locations()) == 2
    assert len(environment.get_user_locations()) == 3


def test_returned_ru_objects_retain_mutable_state() -> None:
    environment = Environment(
        make_config(initial_status=RUStatus.ACTIVE), AlwaysActiveController(), 0.0
    )

    environment.get_rus()[0].set_status(RUStatus.SLEEP)

    assert environment.get_rus()[0].get_status() is RUStatus.SLEEP


def test_update_applies_batteries_before_the_injected_controller() -> None:
    controller = RecordingController()
    environment = Environment(
        make_config(
            ru_count=2,
            user_count=1,
            initial_battery=10.0,
            zero_user_consumption=2.0,
            one_user_consumption=2.0,
            sleep_consumption=0.5,
        ),
        controller,
        0.0,
    )
    active_ru, sleeping_ru = environment.get_rus()
    active_ru.set_status(RUStatus.ACTIVE)
    sleeping_ru.set_status(RUStatus.SLEEP)

    environment.update(1, minimum_service_link_weight=0.0)

    assert controller.received_rus == environment.get_rus()
    assert controller.received_timestamp == 1
    assert active_ru.get_battery() == 8.0
    assert active_ru.get_status() is RUStatus.ACTIVE
    assert sleeping_ru.get_battery() == 9.5
    assert sleeping_ru.get_status() is RUStatus.SLEEP


def test_update_keeps_its_ru_list_isolated_from_controller_result() -> None:
    controller = RecordingController()
    environment = Environment(make_config(ru_count=1, user_count=1), controller, 0.0)

    environment.update(1, minimum_service_link_weight=0.0)
    assert controller.received_rus is not None
    controller.received_rus.clear()

    assert len(environment.get_rus()) == 1


def test_exposes_update_as_its_only_public_update_operation() -> None:
    assert not hasattr(Environment, "set_rus")
    assert not hasattr(Environment, "update_batteries")
    assert not hasattr(Environment, "update_connectivity_graph")


def test_update_charges_an_active_ru_for_only_qualifying_current_links() -> None:
    environment = Environment(
        make_config(
            ru_count=1,
            user_count=3,
            initial_battery=10.0,
            zero_user_consumption=1.0,
            one_user_consumption=2.0,
            multi_user_consumption_per_user=1.5,
        ),
        RecordingController(),
        0.0,
    )
    ru = environment.get_rus()[0]
    users = environment.get_users()
    replace_connectivity_graph(
        environment,
        [
            (ru, users[0], 0.6),
            (ru, users[1], 0.8),
            (ru, users[2], 0.5),
        ],
    )

    environment.update(timestamp=1, minimum_service_link_weight=0.6)

    assert ru.get_battery() == pytest.approx(7.0)


def test_update_charges_an_active_ru_at_zero_user_rate_without_qualifying_links() -> (
    None
):
    environment = Environment(
        make_config(
            ru_count=1,
            user_count=1,
            initial_battery=10.0,
            zero_user_consumption=1.0,
            one_user_consumption=2.0,
            multi_user_consumption_per_user=1.5,
        ),
        RecordingController(),
        0.0,
    )
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]
    replace_connectivity_graph(environment, [(ru, user, 0.5)])

    environment.update(timestamp=1, minimum_service_link_weight=0.6)

    assert ru.get_battery() == pytest.approx(9.0)


def test_propagates_ru_validation_for_invalid_uniform_settings() -> None:
    config = make_config(initial_battery=0.0)

    with pytest.raises(DomainValidationError, match="battery"):
        Environment(config, AlwaysActiveController(), 0.0)


def test_associates_a_user_with_the_highest_weight_qualifying_ru() -> None:
    environment = Environment(
        make_config(ru_count=2, user_count=1, user_capacity=1),
        RecordingController(),
        0.6,
    )
    first_ru, second_ru = environment.get_rus()
    user = environment.get_users()[0]

    rebuild_associations(
        environment, [(first_ru, user, 0.6), (second_ru, user, 0.8)], 0.6
    )

    assert environment.get_associated_ru(user) is second_ru


def test_rejects_edges_below_the_service_threshold_but_accepts_equal_weights() -> None:
    environment = Environment(
        make_config(ru_count=2, user_count=1, user_capacity=1),
        RecordingController(),
        0.6,
    )
    below_threshold_ru, threshold_ru = environment.get_rus()
    user = environment.get_users()[0]

    rebuild_associations(
        environment,
        [(below_threshold_ru, user, 0.59), (threshold_ru, user, 0.6)],
        0.6,
    )

    assert environment.get_associated_ru(user) is threshold_ru


def test_leaves_a_user_unassociated_with_only_a_below_threshold_edge() -> None:
    environment = Environment(
        make_config(ru_count=1, user_count=1, user_capacity=1),
        RecordingController(),
        0.6,
    )
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]

    rebuild_associations(environment, [(ru, user, 0.59)], 0.6)

    assert environment.get_associated_ru(user) is None


def test_falls_back_when_a_higher_ranked_ru_is_full() -> None:
    environment = Environment(
        make_config(ru_count=2, user_count=2, user_capacity=1),
        RecordingController(),
        0.0,
    )
    first_ru, second_ru = environment.get_rus()
    first_user, second_user = environment.get_users()

    rebuild_associations(
        environment,
        [
            (first_ru, first_user, 0.9),
            (first_ru, second_user, 0.8),
            (second_ru, second_user, 0.7),
        ],
        0.0,
    )

    assert environment.get_associated_ru(first_user) is first_ru
    assert environment.get_associated_ru(second_user) is second_ru


def test_leaves_a_user_unassociated_when_all_candidates_are_full() -> None:
    environment = Environment(
        make_config(ru_count=1, user_count=2, user_capacity=1),
        RecordingController(),
        0.0,
    )
    ru = environment.get_rus()[0]
    first_user, second_user = environment.get_users()

    rebuild_associations(
        environment, [(ru, first_user, 0.9), (ru, second_user, 0.8)], 0.0
    )

    assert environment.get_associated_ru(second_user) is None


def test_never_associates_more_users_than_an_ru_capacity() -> None:
    environment = Environment(
        make_config(ru_count=1, user_count=3, user_capacity=2),
        RecordingController(),
        0.0,
    )
    ru = environment.get_rus()[0]
    users = environment.get_users()

    rebuild_associations(environment, [(ru, user, 1.0) for user in users], 0.0)

    assert sum(environment.get_associated_ru(user) is ru for user in users) == 2


@pytest.mark.parametrize(
    "status,deplete_battery", [(RUStatus.SLEEP, False), (RUStatus.ACTIVE, True)]
)
def test_does_not_associate_sleeping_or_depleted_rus(
    status: RUStatus, deplete_battery: bool
) -> None:
    environment = Environment(
        make_config(ru_count=1, user_count=1, initial_status=status),
        RecordingController(),
        0.0,
    )
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]
    if deplete_battery:
        ru.update_battery(delta_time=100.0)

    rebuild_associations(environment, [(ru, user, 1.0)], 0.0)

    assert environment.get_associated_ru(user) is None


def test_breaks_equal_weight_ties_by_lower_ru_id() -> None:
    environment = Environment(
        make_config(ru_count=2, user_count=1, user_capacity=1),
        RecordingController(),
        0.0,
    )
    lower_id_ru, higher_id_ru = environment.get_rus()
    user = environment.get_users()[0]

    rebuild_associations(
        environment, [(higher_id_ru, user, 0.8), (lower_id_ru, user, 0.8)], 0.0
    )

    assert environment.get_associated_ru(user) is lower_id_ru


def test_rebuilds_associations_after_the_controller_activates_an_ru() -> None:
    environment = Environment(
        make_config(
            width=2,
            height=1,
            ru_count=1,
            user_count=1,
            initial_status=RUStatus.SLEEP,
            coverage_radius=2.0,
        ),
        AlwaysActiveController(),
        0.0,
    )
    user = environment.get_users()[0]

    assert environment.get_associated_ru(user) is None

    environment.update(timestamp=1, minimum_service_link_weight=0.0)

    assert environment.get_associated_ru(user) is environment.get_rus()[0]


def test_constructs_an_initial_association_for_an_active_qualifying_ru() -> None:
    environment = Environment(
        make_config(
            width=2,
            height=1,
            ru_count=1,
            user_count=1,
            initial_status=RUStatus.ACTIVE,
            coverage_radius=2.0,
        ),
        AlwaysActiveController(),
        0.0,
    )
    user = environment.get_users()[0]

    assert environment.get_associated_ru(user) is environment.get_rus()[0]
