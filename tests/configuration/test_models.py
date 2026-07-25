from dataclasses import FrozenInstanceError
from typing import get_type_hints

import pytest

from simulator.configuration import ControllerConfig, ControllerKind, SimulationConfig


def test_threshold_percentage_annotation_accepts_integers_and_floats() -> None:
    threshold_annotation = get_type_hints(ControllerConfig)["threshold_percentage"]
    assert threshold_annotation == int | float | None


def test_threshold_controller_accepts_in_range_percentage() -> None:
    config = ControllerConfig(
        kind=ControllerKind.THRESHOLD_STAGGERED_ACTIVE,
        threshold_percentage=50.0,
    )

    assert config.threshold_percentage == 50.0


@pytest.mark.parametrize("threshold", [None, -0.1, 100.1, True, "50"])
def test_threshold_controller_rejects_invalid_percentage(threshold: object) -> None:
    with pytest.raises(ValueError, match="threshold_percentage"):
        ControllerConfig(ControllerKind.THRESHOLD_STAGGERED_ACTIVE, threshold)


@pytest.mark.parametrize(
    "kind", [ControllerKind.ALWAYS_ACTIVE, ControllerKind.STAGGERED_ACTIVE]
)
def test_non_threshold_controller_rejects_threshold(kind: ControllerKind) -> None:
    with pytest.raises(ValueError, match="threshold_percentage"):
        ControllerConfig(kind, 50.0)


def test_controller_configuration_is_immutable() -> None:
    config = ControllerConfig(
        kind=ControllerKind.THRESHOLD_STAGGERED_ACTIVE,
        threshold_percentage=50.0,
    )

    with pytest.raises(FrozenInstanceError):
        config.threshold_percentage = 75.0


def test_simulation_config_accepts_positive_steps() -> None:
    assert SimulationConfig(steps=10_000).steps == 10_000


def test_simulation_configuration_is_immutable() -> None:
    config = SimulationConfig(steps=10_000)

    with pytest.raises(FrozenInstanceError):
        config.steps = 1


@pytest.mark.parametrize("steps", [0, -1, True, 1.5, "10"])
def test_simulation_config_rejects_non_positive_or_non_integer_steps(
    steps: object,
) -> None:
    with pytest.raises(ValueError, match="steps"):
        SimulationConfig(steps=steps)  # type: ignore[arg-type]
