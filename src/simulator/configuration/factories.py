from simulator.configuration.models import ControllerConfig, ControllerKind
from simulator.controllers import (
    AlwaysActiveController,
    RUController,
    StaggeredActiveController,
    ThresholdStaggeredActiveController,
)


def build_controller(config: ControllerConfig) -> RUController:
    if config.kind is ControllerKind.ALWAYS_ACTIVE:
        return AlwaysActiveController()
    if config.kind is ControllerKind.STAGGERED_ACTIVE:
        return StaggeredActiveController()
    if config.kind is ControllerKind.THRESHOLD_STAGGERED_ACTIVE:
        assert config.threshold_percentage is not None
        return ThresholdStaggeredActiveController(config.threshold_percentage)
    raise ValueError(f"unsupported controller kind: {config.kind}")
