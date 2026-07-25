from abc import ABC, abstractmethod

from simulator.environment.environment import Environment


class MetricCollector(ABC):
    @abstractmethod
    def collect(self, environment: Environment) -> None:
        """Observe the environment after a simulation step."""
