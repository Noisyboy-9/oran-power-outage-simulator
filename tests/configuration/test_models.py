from dataclasses import FrozenInstanceError

import pytest

from simulator.configuration import ControllerConfig, ControllerKind


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
