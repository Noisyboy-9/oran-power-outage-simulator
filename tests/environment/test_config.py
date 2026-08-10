from dataclasses import FrozenInstanceError

import pytest

from simulator.domain.ru import RUStatus
from simulator.environment import (
    EnvironmentConfig,
    EnvironmentValidationError,
    MapConfig,
    RUConfig,
)


def make_ru_config(**overrides: object) -> RUConfig:
    values = {
        "count": 2,
        "initial_battery": 100.0,
        "initial_status": RUStatus.ACTIVE,
        "zero_user_consumption": 1.0,
        "one_user_consumption": 2.0,
        "multi_user_consumption_per_user": 1.5,
        "sleep_consumption": 0.5,
        "coverage_radius": 4.0,
    }
    values.update(overrides)
    return RUConfig(**values)  # type: ignore[arg-type]


def make_environment_config(**overrides: object) -> EnvironmentConfig:
    values = {
        "map": MapConfig(width=3, height=2),
        "ru": make_ru_config(),
        "user_count": 2,
        "random_seed": 7,
    }
    values.update(overrides)
    return EnvironmentConfig(**values)  # type: ignore[arg-type]


def test_stores_nested_configuration() -> None:
    config = make_environment_config()

    assert config.map == MapConfig(width=3, height=2)
    assert config.ru == make_ru_config()
    assert config.user_count == 2
    assert config.random_seed == 7


@pytest.mark.parametrize(
    ("config", "field", "value"),
    [
        (MapConfig(2, 2), "width", 3),
        (make_ru_config(), "count", 3),
        (make_environment_config(), "user_count", 3),
    ],
)
def test_configuration_is_immutable(config: object, field: str, value: object) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(config, field, value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("width", 0),
        ("width", -1),
        ("width", 1.5),
        ("width", True),
        ("height", 0),
        ("height", -1),
        ("height", 1.5),
        ("height", False),
    ],
)
def test_rejects_invalid_map_dimensions(field: str, value: object) -> None:
    values = {"width": 2, "height": 2, field: value}

    with pytest.raises(EnvironmentValidationError, match=field):
        MapConfig(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("count", [0, -1, 1.5, True])
def test_rejects_invalid_ru_count(count: object) -> None:
    with pytest.raises(EnvironmentValidationError, match="count"):
        make_ru_config(count=count)


@pytest.mark.parametrize("coverage_radius", [0.0, -1.0, float("nan"), True, "wide"])
def test_rejects_invalid_coverage_radius(coverage_radius: object) -> None:
    with pytest.raises(EnvironmentValidationError, match="coverage_radius"):
        make_ru_config(coverage_radius=coverage_radius)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (field, value)
        for field in (
            "zero_user_consumption",
            "one_user_consumption",
            "multi_user_consumption_per_user",
            "sleep_consumption",
        )
        for value in (0.0, -1.0, True, "1")
    ],
)
def test_rejects_invalid_ru_consumption_rates(field: str, value: object) -> None:
    with pytest.raises(EnvironmentValidationError, match=field):
        make_ru_config(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [("map", object()), ("ru", object())],
)
def test_rejects_invalid_nested_configuration(field: str, value: object) -> None:
    with pytest.raises(EnvironmentValidationError, match=field):
        make_environment_config(**{field: value})


@pytest.mark.parametrize("user_count", [0, -1, 1.5, True])
def test_rejects_invalid_user_count(user_count: object) -> None:
    with pytest.raises(EnvironmentValidationError, match="user_count"):
        make_environment_config(user_count=user_count)


def test_rejects_entity_count_larger_than_map() -> None:
    with pytest.raises(EnvironmentValidationError, match="map capacity"):
        make_environment_config(
            map=MapConfig(width=2, height=2),
            ru=make_ru_config(count=3),
            user_count=2,
        )


def test_accepts_entity_count_equal_to_map_capacity() -> None:
    config = make_environment_config(
        map=MapConfig(width=2, height=2),
        ru=make_ru_config(count=2),
        user_count=2,
    )

    assert config.ru.count + config.user_count == 4


@pytest.mark.parametrize("random_seed", [True, 1.5, "7"])
def test_rejects_invalid_random_seed(random_seed: object) -> None:
    with pytest.raises(EnvironmentValidationError, match="random_seed"):
        make_environment_config(random_seed=random_seed)


@pytest.mark.parametrize("random_seed", [None, 0, -3])
def test_accepts_supported_random_seed(random_seed: int | None) -> None:
    config = make_environment_config(random_seed=random_seed)

    assert config.random_seed == random_seed
