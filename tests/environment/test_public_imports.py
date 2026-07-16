from simulator.environment import (
    EnvironmentConfig,
    EnvironmentValidationError,
    MapConfig,
    RUConfig,
)


def test_environment_configuration_types_are_publicly_importable() -> None:
    assert MapConfig.__name__ == "MapConfig"
    assert RUConfig.__name__ == "RUConfig"
    assert EnvironmentConfig.__name__ == "EnvironmentConfig"
    assert issubclass(EnvironmentValidationError, ValueError)
