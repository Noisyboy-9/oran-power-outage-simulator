from collections.abc import Callable

import pytest

import simulator.simulation as simulation_module
from simulator.configuration import (
    ApplicationConfig,
    ControllerConfig,
    ControllerKind,
    LoggingConfig,
    SimulationConfig,
    TimestampConfig,
)
from simulator.controllers import RUController
from simulator.domain import RU, RUStatus
from simulator.environment import Environment, EnvironmentConfig, MapConfig, RUConfig
from simulator.metrics import MetricCollector
from simulator.simulation import Simulation


def make_application_config(steps: int = 1) -> ApplicationConfig:
    return ApplicationConfig(
        environment=EnvironmentConfig(
            map=MapConfig(width=2, height=1),
            ru=RUConfig(
                count=1,
                initial_battery=10.0,
                initial_status=RUStatus.SLEEP,
                active_consumption=3.0,
                sleep_consumption=1.0,
                coverage_radius=2.0,
            ),
            user_count=1,
            random_seed=7,
        ),
        controller=ControllerConfig(ControllerKind.ALWAYS_ACTIVE),
        logging=LoggingConfig(
            logger_name="simulator",
            level=20,
            destination="stdout",
            format="json",
            include_logger_name=True,
            include_log_level=True,
            timestamp=TimestampConfig(key="logged_at", format="iso", utc=True),
            cache_loggers_on_first_use=True,
            propagate=False,
        ),
        simulation=SimulationConfig(steps=steps),
    )


def test_starts_at_timestamp_zero_with_configured_environment() -> None:
    simulation = Simulation(make_application_config())

    assert simulation.timestamp == 0
    assert len(simulation.environment.get_rus()) == 1
    assert len(simulation.environment.get_users()) == 1


class RecordingCollector(MetricCollector):
    def __init__(self) -> None:
        self.observations: list[tuple[float, RUStatus, float]] = []

    def collect(self, environment: Environment) -> None:
        ru = environment.get_rus()[0]
        user = environment.get_users()[0]
        self.observations.append(
            (
                ru.get_battery(),
                ru.get_status(),
                environment.get_connection_weight(user, ru),
            )
        )


class RecordingController(RUController):
    def __init__(self, lifecycle: list[tuple[str, int]]) -> None:
        self._lifecycle = lifecycle
        self.received_rus: list[RU] | None = None
        self.received_timestamp: int | None = None

    def update(self, rus: list[RU], timestamp: int) -> list[RU]:
        self.received_rus = rus
        self.received_timestamp = timestamp
        self._lifecycle.append(("controller", timestamp))
        return rus


class LifecycleCollector(MetricCollector):
    def __init__(
        self,
        lifecycle: list[tuple[str, int]],
        timestamp: Callable[[], int],
        component_environments: list[Environment],
    ) -> None:
        self._lifecycle = lifecycle
        self._timestamp = timestamp
        self._component_environments = component_environments

    def collect(self, environment: Environment) -> None:
        self._component_environments.append(environment)
        self._lifecycle.append(("collector", self._timestamp()))


def test_simulate_coordinates_managed_environment_in_exact_lifecycle_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[tuple[str, int]] = []
    component_environments: list[Environment] = []
    controller = RecordingController(lifecycle)
    simulation: Simulation
    collector = LifecycleCollector(
        lifecycle,
        lambda: simulation.timestamp,
        component_environments,
    )
    monkeypatch.setattr(
        simulation_module,
        "build_controller",
        lambda _config: controller,
    )
    simulation = Simulation(make_application_config(), [collector])
    environment = simulation.environment
    original_get_rus = environment.get_rus
    expected_rus = original_get_rus()

    def record_battery_update() -> None:
        lifecycle.append(("timestamp", simulation.timestamp))
        lifecycle.append(("batteries", simulation.timestamp))
        component_environments.append(environment)

    def get_rus_for_controller() -> list[RU]:
        component_environments.append(environment)
        return original_get_rus()

    def record_graph_update() -> None:
        component_environments.append(environment)
        lifecycle.append(("graph", simulation.timestamp))

    monkeypatch.setattr(environment, "update_batteries", record_battery_update)
    monkeypatch.setattr(environment, "get_rus", get_rus_for_controller)
    monkeypatch.setattr(
        environment,
        "update_connectivity_graph",
        record_graph_update,
    )

    simulation.simulate()

    assert lifecycle == [
        ("timestamp", 1),
        ("batteries", 1),
        ("controller", 1),
        ("graph", 1),
        ("collector", 1),
    ]
    assert controller.received_timestamp == 1
    assert controller.received_rus is not None
    assert all(
        received is expected
        for received, expected in zip(
            controller.received_rus,
            expected_rus,
            strict=True,
        )
    )
    assert len(component_environments) == 4
    assert all(
        component_environment is environment
        for component_environment in component_environments
    )


def test_simulate_updates_state_before_collecting_metrics() -> None:
    collector = RecordingCollector()
    simulation = Simulation(make_application_config(), [collector])
    ru = simulation.environment.get_rus()[0]
    user = simulation.environment.get_users()[0]
    initial_weight = simulation.environment.get_connection_weight(user, ru)

    simulation.simulate()

    assert simulation.timestamp == 1
    assert ru.get_battery() == 9.0
    assert ru.get_status() is RUStatus.ACTIVE
    assert collector.observations == [
        (9.0, RUStatus.ACTIVE, simulation.environment.get_connection_weight(user, ru))
    ]
    assert collector.observations[0][2] != initial_weight


def test_simulate_uses_the_status_selected_by_the_previous_iteration() -> None:
    simulation = Simulation(make_application_config(steps=2))

    simulation.simulate()

    ru = simulation.environment.get_rus()[0]
    assert simulation.timestamp == 2
    assert ru.get_battery() == 6.0
    assert ru.get_status() is RUStatus.ACTIVE
