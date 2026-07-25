from simulator.configuration import MetricKind, MetricsConfig
from simulator.metrics.average_emergency_qos import AverageEmergencyQoSCollector
from simulator.metrics.average_ru_battery_depletion_time import (
    AverageRUBatteryDepletionTimeCollector,
)
from simulator.metrics.base import MetricCollector
from simulator.metrics.network_lifetime import NetworkLifetimeCollector


def build_metric_collectors(config: MetricsConfig) -> list[MetricCollector]:
    collectors: list[MetricCollector] = []
    for kind in config.collectors:
        if kind is MetricKind.NETWORK_LIFETIME:
            collector = NetworkLifetimeCollector(
                config.minimum_emergency_service_fraction,
                config.minimum_service_link_weight,
            )
        elif kind is MetricKind.AVERAGE_EMERGENCY_QOS:
            collector = AverageEmergencyQoSCollector(config.minimum_service_link_weight)
        elif kind is MetricKind.AVERAGE_RU_BATTERY_DEPLETION_TIME:
            collector = AverageRUBatteryDepletionTimeCollector()
        collectors.append(collector)
    return collectors
