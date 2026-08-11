from simulator.environment import Environment
from simulator.metrics.base import MetricCollector
from simulator.metrics.service import _served_user_fraction


class NetworkLifetimeCollector(MetricCollector):
    name = "network_lifetime"

    def __init__(
        self,
        minimum_emergency_service_fraction: float,
    ) -> None:
        super().__init__()
        if (
            isinstance(minimum_emergency_service_fraction, bool)
            or not isinstance(minimum_emergency_service_fraction, (int, float))
            or not 0 < minimum_emergency_service_fraction <= 1
        ):
            raise ValueError(
                "minimum_emergency_service_fraction must be a number between 0 and 1"
            )
        self.minimum_emergency_service_fraction = minimum_emergency_service_fraction
        self._served_fractions: dict[int, float] = {}

    def _collect(self, environment: Environment, timestamp: int) -> None:
        self._served_fractions[timestamp] = _served_user_fraction(environment)

    def _observation_records(self) -> list[dict[str, object]]:
        return [
            {"timestamp": timestamp, "served_user_fraction": served_fraction}
            for timestamp, served_fraction in sorted(self._served_fractions.items())
        ]

    def finish_calculation(self) -> float:
        self._require_observation()
        for timestamp, served_fraction in sorted(self._served_fractions.items()):
            if served_fraction < self.minimum_emergency_service_fraction:
                return 0.0 if timestamp == 0 else float(timestamp - 1)
        return float("inf")
