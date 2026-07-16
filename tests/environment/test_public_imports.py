from simulator.environment import (
    Environment,
    EnvironmentConfig,
    EnvironmentValidationError,
    MapConfig,
    RUConfig,
)


def test_environment_types_are_publicly_importable() -> None:
    assert Environment.__name__ == "Environment"
    assert MapConfig.__name__ == "MapConfig"
    assert RUConfig.__name__ == "RUConfig"
    assert EnvironmentConfig.__name__ == "EnvironmentConfig"
    assert issubclass(EnvironmentValidationError, ValueError)
