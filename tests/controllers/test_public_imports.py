from simulator.controllers import (
    AlwaysActiveController,
    RUController,
    StaggeredActiveController,
    ThresholdStaggeredActiveController,
)


def test_controller_classes_are_publicly_importable() -> None:
    assert AlwaysActiveController.__name__ == "AlwaysActiveController"
    assert RUController.__name__ == "RUController"
    assert StaggeredActiveController.__name__ == "StaggeredActiveController"
    assert (
        ThresholdStaggeredActiveController.__name__
        == "ThresholdStaggeredActiveController"
    )
