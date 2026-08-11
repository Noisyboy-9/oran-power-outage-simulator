from simulator.environment import Environment
from simulator.metrics.base import MetricCollector
from simulator.metrics.service import (
    _served_user_fraction,
    _validate_minimum_service_link_weight,
)


class AverageEmergencyQoSCollector(MetricCollector):
    name = "average_emergency_qos"

    def __init__(self, minimum_service_link_weight: float) -> None:
        super().__init__()
        _validate_minimum_service_link_weight(minimum_service_link_weight)
        self.minimum_service_link_weight = minimum_service_link_weight
        self._served_fractions: dict[int, float] = {}

    def _collect(self, environment: Environment, timestamp: int) -> None:
        self._served_fractions[timestamp] = _served_user_fraction(
            environment, self.minimum_service_link_weight
        )

    def _observation_records(self) -> list[dict[str, object]]:
        return [
            {"timestamp": timestamp, "served_user_fraction": served_fraction}
            for timestamp, served_fraction in sorted(self._served_fractions.items())
        ]

    def finish_calculation(self) -> float:
        self._require_observation()
        return sum(self._served_fractions.values()) / len(self._served_fractions)
