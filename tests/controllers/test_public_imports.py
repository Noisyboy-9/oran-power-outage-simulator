from inspect import signature

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


def test_controller_updates_name_the_ru_list_rus() -> None:
    controller_types = (
        RUController,
        AlwaysActiveController,
        StaggeredActiveController,
        ThresholdStaggeredActiveController,
    )

    for controller_type in controller_types:
        parameter_names = list(signature(controller_type.update).parameters)
        assert parameter_names == ["self", "rus", "timestamp"]
