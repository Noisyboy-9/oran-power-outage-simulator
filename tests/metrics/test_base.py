import pytest

from simulator.environment import Environment
from simulator.metrics import MetricCollector


class RecordingCollector(MetricCollector):
    name = "recording"

    def __init__(self) -> None:
        super().__init__()
        self.timestamps: list[int] = []

    def _collect(self, environment: Environment, timestamp: int) -> None:
        self.timestamps.append(timestamp)

    def finish_calculation(self) -> float:
        self._require_observation()
        return float(len(self.timestamps))


def test_metric_collector_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        MetricCollector()


def test_finishing_before_an_observation_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot finish"):
        RecordingCollector().finish_calculation()


def test_collector_records_consecutive_timestamps_starting_at_zero() -> None:
    collector = RecordingCollector()
    environment = object()

    collector.collect(environment, 0)  # type: ignore[arg-type]
    collector.collect(environment, 1)  # type: ignore[arg-type]

    assert collector.timestamps == [0, 1]
    assert collector.finish_calculation() == 2.0


@pytest.mark.parametrize("timestamp", [-1, True, 1])
def test_first_timestamp_must_be_zero_integer(timestamp: int) -> None:
    collector = RecordingCollector()

    with pytest.raises(ValueError, match="next non-negative integer"):
        collector.collect(object(), timestamp)  # type: ignore[arg-type]

    assert collector.timestamps == []


@pytest.mark.parametrize("second_timestamp", [0, 2])
def test_collector_rejects_duplicate_or_skipped_timestamps(
    second_timestamp: int,
) -> None:
    collector = RecordingCollector()
    environment = object()
    collector.collect(environment, 0)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="next non-negative integer"):
        collector.collect(environment, second_timestamp)  # type: ignore[arg-type]

    assert collector.timestamps == [0]
