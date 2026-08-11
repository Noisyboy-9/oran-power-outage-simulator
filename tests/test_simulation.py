import pytest

import simulator.simulation as simulation_module
from simulator.configuration import (
    ApplicationConfig,
    ControllerConfig,
    ControllerKind,
    LoggingConfig,
    MetricsConfig,
    SimulationConfig,
    TimestampConfig,
)
from simulator.domain import RUStatus
from simulator.environment import Environment, EnvironmentConfig, MapConfig, RUConfig
from simulator.metrics import MetricCollector
from simulator.simulation import Simulation


def make_application_config(
    steps: int = 1, minimum_service_link_weight: float = 0.0
) -> ApplicationConfig:
    return ApplicationConfig(
        environment=EnvironmentConfig(
            map=MapConfig(width=2, height=1),
            ru=RUConfig(
                count=1,
                initial_battery=10.0,
                initial_status=RUStatus.SLEEP,
                zero_user_consumption=3.0,
                one_user_consumption=2.0,
                multi_user_consumption_per_user=1.5,
                sleep_consumption=1.0,
                user_capacity=100,
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
        simulation=SimulationConfig(
            steps=steps,
            metrics=MetricsConfig(
                collectors=(),
                minimum_emergency_service_fraction=0.8,
                minimum_service_link_weight=minimum_service_link_weight,
            ),
        ),
    )


def test_starts_at_timestamp_zero_with_configured_environment() -> None:
    simulation = Simulation(make_application_config())

    assert simulation.timestamp == 0
    assert len(simulation.environment.get_rus()) == 1
    assert len(simulation.environment.get_users()) == 1
    assert not hasattr(simulation, "_initial_metrics_collected")


class RecordingCollector(MetricCollector):
    def __init__(self) -> None:
        super().__init__()
        self.observations: list[tuple[int, float, RUStatus, float]] = []

    @property
    def name(self) -> str:
        return "recording"

    def _collect(self, environment: Environment, timestamp: int) -> None:
        ru = environment.get_rus()[0]
        user = environment.get_users()[0]
        self.observations.append(
            (
                timestamp,
                ru.get_battery(),
                ru.get_status(),
                environment.get_connection_weight(user, ru),
            )
        )

    def finish_calculation(self) -> float:
        self._require_observation()
        return float(len(self.observations))

    def _observation_records(self) -> list[dict[str, object]]:
        return []


class RecordingEnvironment:
    def __init__(
        self, lifecycle: list[str], minimum_service_link_weight: float
    ) -> None:
        self._lifecycle = lifecycle
        self.minimum_service_link_weight = minimum_service_link_weight
        self.updates: list[tuple[int, float]] = []

    def update(self, timestamp: int, minimum_service_link_weight: float) -> None:
        self.updates.append((timestamp, minimum_service_link_weight))
        self._lifecycle.append(f"environment.update:{timestamp}")


class LifecycleCollector(MetricCollector):
    def __init__(
        self,
        lifecycle: list[str],
        component_environments: list[Environment],
    ) -> None:
        super().__init__()
        self._lifecycle = lifecycle
        self._component_environments = component_environments

    @property
    def name(self) -> str:
        return "lifecycle"

    def _collect(self, environment: Environment, timestamp: int) -> None:
        self._component_environments.append(environment)
        self._lifecycle.append(f"collector.collect:{timestamp}")

    def finish_calculation(self) -> float:
        self._require_observation()
        return float(len(self._component_environments))

    def _observation_records(self) -> list[dict[str, object]]:
        return []


def test_simulate_delegates_environment_update_before_collecting_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []
    component_environments: list[Environment] = []
    controller = object()
    collector = LifecycleCollector(
        lifecycle,
        component_environments,
    )
    monkeypatch.setattr(
        simulation_module,
        "build_controller",
        lambda _config: controller,
    )
    environment: RecordingEnvironment | None = None

    def create_environment(
        _config: EnvironmentConfig,
        _controller: object,
        minimum_service_link_weight: float,
    ) -> RecordingEnvironment:
        nonlocal environment
        environment = RecordingEnvironment(lifecycle, minimum_service_link_weight)
        return environment

    monkeypatch.setattr(
        simulation_module,
        "Environment",
        create_environment,
    )
    simulation = Simulation(
        make_application_config(minimum_service_link_weight=0.73), [collector]
    )

    assert environment is not None
    assert environment.minimum_service_link_weight == 0.73

    simulation.simulate()

    assert lifecycle == [
        "collector.collect:0",
        "environment.update:1",
        "collector.collect:1",
    ]
    assert component_environments == [environment, environment]
    assert environment.updates == [(1, 0.73)]


def test_simulate_collects_initial_state_once_and_each_updated_state() -> None:
    collector = RecordingCollector()
    simulation = Simulation(make_application_config(steps=2), [collector])
    ru = simulation.environment.get_rus()[0]
    user = simulation.environment.get_users()[0]
    initial_weight = simulation.environment.get_connection_weight(user, ru)

    simulation.simulate()

    assert simulation.timestamp == 2
    assert [observation[0] for observation in collector.observations] == [0, 1, 2]
    assert collector.observations[0] == (
        0,
        10.0,
        RUStatus.SLEEP,
        initial_weight,
    )
    assert collector.observations[1][1:3] == (
        9.0,
        RUStatus.ACTIVE,
    )
    assert collector.observations[1][3] != initial_weight
    assert ru.get_battery() == 7.0
    assert ru.get_status() is RUStatus.ACTIVE


def test_simulate_uses_the_status_selected_by_the_previous_iteration() -> None:
    simulation = Simulation(make_application_config(steps=2))

    simulation.simulate()

    ru = simulation.environment.get_rus()[0]
    assert simulation.timestamp == 2
    assert ru.get_battery() == 7.0
    assert ru.get_status() is RUStatus.ACTIVE
