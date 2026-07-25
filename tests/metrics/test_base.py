import pytest

from simulator.metrics import MetricCollector


def test_metric_collector_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        MetricCollector()
