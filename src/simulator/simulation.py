from collections.abc import Iterable

from simulator.configuration import ApplicationConfig, build_controller
from simulator.environment import Environment
from simulator.metrics import MetricCollector


class Simulation:
    def __init__(
        self,
        config: ApplicationConfig,
        metric_collectors: Iterable[MetricCollector] = (),
    ) -> None:
        self._config = config
        self._timestamp = 0
        self._environment = Environment(
            config.environment,
            build_controller(config.controller),
        )
        self._metric_collectors = list(metric_collectors)
        self._initial_metrics_collected = False

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    def environment(self) -> Environment:
        return self._environment

    def simulate(self) -> None:
        self._collect_initial_metrics()
        for _ in range(self._config.simulation.steps):
            self._step()

    def _collect_initial_metrics(self) -> None:
        if self._initial_metrics_collected:
            return

        # Metrics include the initial state because their definitions start at t=0.
        for collector in self._metric_collectors:
            collector.collect(self._environment, self._timestamp)
        self._initial_metrics_collected = True

    def _step(self) -> None:
        self._timestamp += 1
        self._environment.update(self._timestamp)
        for collector in self._metric_collectors:
            collector.collect(self._environment, self._timestamp)
