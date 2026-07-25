import math

import pytest
from conftest import FakeEnvironment

from simulator.domain import RU, RUStatus
from simulator.metrics.average_ru_battery_depletion_time import (
    AverageRUBatteryDepletionTimeCollector,
)


def make_environment() -> FakeEnvironment:
    return FakeEnvironment(
        [],
        [
            RU(1, 2.0, RUStatus.ACTIVE, 1.0, 0.5),
            RU(2, 3.0, RUStatus.ACTIVE, 1.0, 0.5),
        ],
    )


def set_batteries(environment: FakeEnvironment, batteries: dict[int, float]) -> None:
    for ru in environment.get_rus():
        ru._battery = batteries[ru.id]


def test_average_ru_battery_depletion_time_uses_first_zero_observations() -> None:
    environment = make_environment()
    collector = AverageRUBatteryDepletionTimeCollector()

    collector.collect(environment, 0)  # {1: 2.0, 2: 3.0}
    set_batteries(environment, {1: 0.0, 2: 1.0})
    collector.collect(environment, 1)
    set_batteries(environment, {1: 0.0, 2: 0.0})
    collector.collect(environment, 2)

    assert collector.name == "average_ru_battery_depletion_time"
    assert collector.finish_calculation() == 1.5


def test_average_ru_battery_depletion_time_uses_an_exact_zero_at_t0() -> None:
    environment = make_environment()
    set_batteries(environment, {1: 0.0, 2: 0.0})
    collector = AverageRUBatteryDepletionTimeCollector()

    collector.collect(environment, 0)

    assert collector.finish_calculation() == 0.0


def test_average_ru_battery_depletion_time_preserves_first_depletion() -> None:
    environment = make_environment()
    collector = AverageRUBatteryDepletionTimeCollector()

    collector.collect(environment, 0)
    set_batteries(environment, {1: 0.0, 2: 0.0})
    collector.collect(environment, 1)
    set_batteries(environment, {1: 5.0, 2: 5.0})
    collector.collect(environment, 2)

    assert collector.finish_calculation() == 1.0


@pytest.mark.parametrize("batteries", [{1: 0.0, 2: 1.0}, {1: 1.0, 2: 1.0}])
def test_average_ru_battery_depletion_time_is_infinite_when_a_ru_survives(
    batteries: dict[int, float],
) -> None:
    environment = make_environment()
    collector = AverageRUBatteryDepletionTimeCollector()

    set_batteries(environment, batteries)
    collector.collect(environment, 0)

    assert math.isinf(collector.finish_calculation())
