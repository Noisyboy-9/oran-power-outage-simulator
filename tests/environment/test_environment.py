import pytest

from simulator.domain.errors import DomainValidationError
from simulator.domain.ru import RUStatus
from simulator.environment import (
    Environment,
    EnvironmentConfig,
    MapConfig,
    RUConfig,
)


def make_config(
    *,
    width: int = 4,
    height: int = 3,
    ru_count: int = 2,
    user_count: int = 3,
    initial_battery: float = 100.0,
    initial_status: RUStatus = RUStatus.ACTIVE,
    active_consumption: float = 2.0,
    sleep_consumption: float = 0.5,
    coverage_radius: float = 4.0,
    random_seed: int | None = 7,
) -> EnvironmentConfig:
    return EnvironmentConfig(
        map=MapConfig(width=width, height=height),
        ru=RUConfig(
            count=ru_count,
            initial_battery=initial_battery,
            initial_status=initial_status,
            active_consumption=active_consumption,
            sleep_consumption=sleep_consumption,
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


def test_creates_row_major_map() -> None:
    environment = Environment(make_config(width=4, height=3))

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
            active_consumption=3.0,
            sleep_consumption=0.25,
        )
    )

    rus = environment.get_rus()
    users = environment.get_users()
    assert [ru.id for ru in rus] == [1, 2]
    assert [user.id for user in users] == [1, 2, 3]
    for ru in rus:
        assert ru.get_battery() == 80.0
        assert ru.get_initial_capacity() == 80.0
        assert ru.get_status() is RUStatus.SLEEP
        assert ru.active_consumption == 3.0
        assert ru.sleep_consumption == 0.25


def test_places_every_entity_in_one_distinct_cell() -> None:
    environment = Environment(make_config())

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
    first = Environment(make_config(random_seed=19))
    second = Environment(make_config(random_seed=19))

    assert placement_signature(first) == placement_signature(second)


def test_collection_getters_protect_environment_structure() -> None:
    environment = Environment(make_config())

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
    environment = Environment(make_config(initial_status=RUStatus.ACTIVE))

    environment.get_rus()[0].set_status(RUStatus.SLEEP)

    assert environment.get_rus()[0].get_status() is RUStatus.SLEEP


def test_propagates_ru_validation_for_invalid_uniform_settings() -> None:
    config = make_config(initial_battery=0.0)

    with pytest.raises(DomainValidationError, match="battery"):
        Environment(config)
