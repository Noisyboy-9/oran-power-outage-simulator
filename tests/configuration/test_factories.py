import pytest

from simulator.configuration import ControllerConfig, ControllerKind, build_controller
from simulator.controllers import (
    AlwaysActiveController,
    StaggeredActiveController,
    ThresholdStaggeredActiveController,
)


@pytest.mark.parametrize(
    ("config", "controller_type"),
    [
        (ControllerConfig(ControllerKind.ALWAYS_ACTIVE), AlwaysActiveController),
        (ControllerConfig(ControllerKind.STAGGERED_ACTIVE), StaggeredActiveController),
    ],
)
def test_build_controller_creates_requested_controller(
    config: ControllerConfig,
    controller_type: type[AlwaysActiveController | StaggeredActiveController],
) -> None:
    assert isinstance(build_controller(config), controller_type)


def test_build_controller_preserves_threshold_percentage() -> None:
    controller = build_controller(
        ControllerConfig(ControllerKind.THRESHOLD_STAGGERED_ACTIVE, 42.5)
    )

    assert isinstance(controller, ThresholdStaggeredActiveController)
    assert controller.threshold_percentage == 42.5
