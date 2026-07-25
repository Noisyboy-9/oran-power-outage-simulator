from simulator.environment import Environment
from simulator.metrics.base import MetricCollector
from simulator.metrics.service import _served_user_fraction


class AverageEmergencyQoSCollector(MetricCollector):
    name = "average_emergency_qos"

    def __init__(self) -> None:
        super().__init__()
        self._served_fractions: dict[int, float] = {}

    def _collect(self, environment: Environment, timestamp: int) -> None:
        self._served_fractions[timestamp] = _served_user_fraction(environment)

    def finish_calculation(self) -> float:
        self._require_observation()
        return sum(self._served_fractions.values()) / len(self._served_fractions)
