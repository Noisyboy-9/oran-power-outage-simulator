from abc import ABC, abstractmethod

from simulator.environment import Environment


class MetricCollector(ABC):
    def __init__(self) -> None:
        self._last_collected_timestamp: int | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable configuration name for this collector."""

    def collect(self, environment: Environment, timestamp: int) -> None:
        expected_timestamp = (
            0
            if self._last_collected_timestamp is None
            else self._last_collected_timestamp + 1
        )
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, int)
            or timestamp != expected_timestamp
        ):
            raise ValueError("timestamp must be the next non-negative integer")
        self._collect(environment, timestamp)
        self._last_collected_timestamp = timestamp

    @abstractmethod
    def _collect(self, environment: Environment, timestamp: int) -> None:
        """Record this collector's observation for one timestamp."""

    def _require_observation(self) -> None:
        if self._last_collected_timestamp is None:
            raise ValueError("cannot finish a metric before collecting an observation")

    @abstractmethod
    def finish_calculation(self) -> float:
        """Return this metric after its final observation."""
