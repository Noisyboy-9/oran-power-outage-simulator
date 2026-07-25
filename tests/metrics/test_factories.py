from simulator.configuration import MetricKind, MetricsConfig
from simulator.metrics import (
    AverageEmergencyQoSCollector,
    AverageRUBatteryDepletionTimeCollector,
    NetworkLifetimeCollector,
    build_metric_collectors,
)


def test_builds_collectors_in_configuration_order_with_lifetime_sla() -> None:
    collectors = build_metric_collectors(
        MetricsConfig(
            collectors=(
                MetricKind.NETWORK_LIFETIME,
                MetricKind.AVERAGE_EMERGENCY_QOS,
            ),
            minimum_emergency_service_fraction=0.75,
            minimum_service_link_weight=0.0,
        )
    )

    assert [collector.name for collector in collectors] == [
        "network_lifetime",
        "average_emergency_qos",
    ]
    assert isinstance(collectors[0], NetworkLifetimeCollector)
    assert collectors[0].minimum_emergency_service_fraction == 0.75
    assert isinstance(collectors[1], AverageEmergencyQoSCollector)


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
