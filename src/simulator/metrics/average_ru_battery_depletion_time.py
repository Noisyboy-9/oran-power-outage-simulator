from simulator.environment import Environment
from simulator.metrics.base import MetricCollector


class AverageRUBatteryDepletionTimeCollector(MetricCollector):
    name = "average_ru_battery_depletion_time"

    def __init__(self) -> None:
        super().__init__()
        self._battery_snapshots: dict[int, dict[int, float]] = {}

    def _collect(self, environment: Environment, timestamp: int) -> None:
        self._battery_snapshots[timestamp] = {
            ru.id: ru.get_battery() for ru in environment.get_rus()
        }

    def _observation_records(self) -> list[dict[str, object]]:
        return [
            {
                "timestamp": timestamp,
                "ru_batteries": {
                    str(ru_id): battery for ru_id, battery in snapshot.items()
                },
            }
            for timestamp, snapshot in sorted(self._battery_snapshots.items())
        ]

    def finish_calculation(self) -> float:
        self._require_observation()
        initial_snapshot = self._battery_snapshots[0]
        depletion_times: list[float] = []
        for ru_id in initial_snapshot:
            depletion_time = next(
                (
                    float(timestamp)
                    for timestamp, snapshot in sorted(self._battery_snapshots.items())
                    if snapshot[ru_id] <= 0
                ),
                float("inf"),
            )
            depletion_times.append(depletion_time)
        return sum(depletion_times) / len(depletion_times)
