from simulator.configuration import MetricKind, MetricsConfig
from simulator.metrics import (
    AverageEmergencyQoSCollector,
    AverageRUBatteryDepletionTimeCollector,
    NetworkLifetimeCollector,
    build_metric_collectors,
)


def test_builds_collectors_in_configuration_order() -> None:
    collectors = build_metric_collectors(
        MetricsConfig(
            collectors=(
                MetricKind.AVERAGE_EMERGENCY_QOS,
                MetricKind.AVERAGE_RU_BATTERY_DEPLETION_TIME,
                MetricKind.NETWORK_LIFETIME,
            ),
            minimum_emergency_service_fraction=0.8,
            minimum_service_link_weight=0.6,
        )
    )

    assert [collector.name for collector in collectors] == [
        "average_emergency_qos",
        "average_ru_battery_depletion_time",
        "network_lifetime",
    ]
    assert isinstance(collectors[0], AverageEmergencyQoSCollector)
    assert not hasattr(collectors[0], "minimum_service_link_weight")
    assert isinstance(collectors[1], AverageRUBatteryDepletionTimeCollector)
    assert isinstance(collectors[2], NetworkLifetimeCollector)
    assert collectors[2].minimum_emergency_service_fraction == 0.8
    assert not hasattr(collectors[2], "minimum_service_link_weight")


def test_builds_average_ru_battery_depletion_time_collector() -> None:
    collectors = build_metric_collectors(
        MetricsConfig(
            collectors=(MetricKind.AVERAGE_RU_BATTERY_DEPLETION_TIME,),
            minimum_emergency_service_fraction=0.8,
            minimum_service_link_weight=0.0,
        )
    )

    assert len(collectors) == 1
    assert isinstance(collectors[0], AverageRUBatteryDepletionTimeCollector)


def test_empty_collector_configuration_builds_an_empty_list() -> None:
    collectors = build_metric_collectors(
        MetricsConfig(
            collectors=(),
            minimum_emergency_service_fraction=0.8,
            minimum_service_link_weight=0.0,
        )
    )

    assert collectors == []
