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
        self._environment = Environment(config.environment)
        self._controller = build_controller(config.controller)
        self._metric_collectors = list(metric_collectors)

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    def environment(self) -> Environment:
        return self._environment

    def simulate(self) -> None:
        for _ in range(self._config.simulation.steps):
            self._step()

    def _step(self) -> None:
        self._timestamp += 1
        self._environment.update_batteries()
        self._controller.update(self._environment.get_rus(), self._timestamp)
        self._environment.update_connectivity_graph()
        for collector in self._metric_collectors:
            collector.collect(self._environment)
