import json
import math
from abc import ABC, abstractmethod
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile

from simulator.configuration import ApplicationConfig
from simulator.environment import Environment


def _json_default(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


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

    @abstractmethod
    def _observation_records(self) -> list[dict[str, object]]:
        """Return timestamp-ordered JSON-ready observations for this metric."""

    def _require_observation(self) -> None:
        if self._last_collected_timestamp is None:
            raise ValueError("cannot finish a metric before collecting an observation")

    @abstractmethod
    def finish_calculation(self) -> float:
        """Return this metric after its final observation."""

    def write_output(self, output_directory: Path, config: ApplicationConfig) -> Path:
        self._require_observation()
        result = self.finish_calculation()
        output_directory.mkdir(parents=True, exist_ok=True)
        output_path = output_directory / f"{self.name}.json"
        payload = {
            "input_configuration": asdict(config),
            "collector": self.name,
            "observations": self._observation_records(),
            "final_result": None if math.isinf(result) else result,
        }
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=output_directory,
                prefix=f".{self.name}-",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(
                    payload,
                    temporary_file,
                    indent=2,
                    allow_nan=False,
                    default=_json_default,
                )
                temporary_file.write("\n")
            temporary_path.replace(output_path)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
        return output_path
