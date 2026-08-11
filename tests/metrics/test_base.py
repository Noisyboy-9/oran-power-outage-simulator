import json
from pathlib import Path

import pytest
from conftest import make_application_config

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

    def _observation_records(self) -> list[dict[str, object]]:
        return [{"timestamp": timestamp} for timestamp in self.timestamps]


class InfiniteCollector(MetricCollector):
    name = "infinite"

    def _collect(self, environment: Environment, timestamp: int) -> None:
        pass

    def finish_calculation(self) -> float:
        self._require_observation()
        return float("inf")

    def _observation_records(self) -> list[dict[str, object]]:
        return []


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


def test_write_output_creates_self_contained_json_and_replaces_existing_file(
    tmp_path: Path,
) -> None:
    collector = RecordingCollector()
    collector.collect(object(), 0)  # type: ignore[arg-type]
    collector.collect(object(), 1)  # type: ignore[arg-type]
    output_directory = tmp_path / "nested" / "results"
    output_path = output_directory / "recording.json"
    output_directory.mkdir(parents=True)
    output_path.write_text("stale", encoding="utf-8")

    assert (
        collector.write_output(output_directory, make_application_config())
        == output_path
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert list(payload) == [
        "input_configuration",
        "collector",
        "observations",
        "final_result",
    ]
    assert payload["input_configuration"]["environment"]["random_seed"] == 7
    assert (
        payload["input_configuration"]["environment"]["ru"]["initial_status"]
        == "active"
    )
    assert payload["collector"] == "recording"
    assert payload["observations"] == [{"timestamp": 0}, {"timestamp": 1}]
    assert payload["final_result"] == 2.0


def test_write_output_creates_missing_directory(tmp_path: Path) -> None:
    collector = RecordingCollector()
    collector.collect(object(), 0)  # type: ignore[arg-type]

    output_path = collector.write_output(
        tmp_path / "new" / "results", make_application_config()
    )

    assert output_path.is_file()


def test_write_output_rejects_an_unobserved_collector(tmp_path: Path) -> None:
    output_directory = tmp_path / "results"

    with pytest.raises(ValueError, match="cannot finish"):
        RecordingCollector().write_output(output_directory, make_application_config())

    assert not output_directory.exists()


def test_write_output_encodes_an_infinite_result_as_json_null(tmp_path: Path) -> None:
    collector = InfiniteCollector()
    collector.collect(object(), 0)  # type: ignore[arg-type]

    payload = json.loads(
        collector.write_output(tmp_path, make_application_config()).read_text(
            encoding="utf-8"
        )
    )

    assert payload["final_result"] is None
