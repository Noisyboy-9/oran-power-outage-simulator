# Service Link Threshold Design

## Goal

Refine the definition of a served user for service-based metrics. A user is
served by an RU only when all of these conditions hold:

1. the environment connectivity graph contains the user-RU association;
2. the RU status is `ACTIVE`;
3. the RU has remaining battery capacity (`battery > 0`); and
4. the association's link weight is at least the configured minimum service
   link weight.

This definition affects Average Emergency QoS and Network Lifetime. Average RU
Battery Depletion Time continues to observe battery levels only.

## Configuration

Add `minimum_service_link_weight` to the required `simulation.metrics` block:

```yaml
simulation:
  steps: 10000
  metrics:
    collectors:
      - average_emergency_qos
      - average_ru_battery_depletion_time
      - network_lifetime
    minimum_emergency_service_fraction: 0.8
    minimum_service_link_weight: 0.3
```

`MetricsConfig` gains an immutable
`minimum_service_link_weight: float` field. The YAML loader requires the key
and rejects unknown metrics keys as before. The value must be a non-boolean
number in the inclusive range `[0, 1]`.

`0.0` is valid and means that every *existing* graph association passes the
link-quality filter. It does not serve users through absent edges: edge
existence remains an independent required condition.

## Collector Construction

Metric selection remains in `main.py` through the existing metric factory.
The factory passes the configured service-link threshold to:

- `AverageEmergencyQoSCollector`; and
- `NetworkLifetimeCollector`, along with its existing minimum emergency-service
  fraction.

`AverageRUBatteryDepletionTimeCollector` receives no threshold because its
calculation is independent of user service.

Both service-based collector constructors validate their threshold directly,
using the same `[0, 1]` non-boolean rule as configuration. This keeps direct
construction safe in tests and future callers without introducing global
configuration state.

## Service Observation

The shared private service helper accepts the threshold explicitly. For each
user and candidate RU, it first verifies that the environment's connectivity
graph contains an edge. It then requires the RU to be active, have a battery
strictly greater than zero, and have an edge weight greater than or equal to
the threshold. A user with one or more qualifying RUs is counted once.

Checking edge presence separately is essential: `get_connection_weight()`
returns `0.0` when an edge is absent, and a threshold of `0.0` must not convert
that sentinel into service.

The environment's graph construction, random weights, controllers, and battery
update behavior remain unchanged. The threshold applies only while metrics
interpret the current state.

## Testing

Configuration tests cover successful loading and direct construction at `0.0`,
an interior value, and `1.0`; reject negative, above-one, boolean, non-numeric,
missing, and unknown-key cases; and update all direct configuration fixtures.

Service-helper tests prove that:

- a positive-weight edge below the threshold does not serve a user;
- a weight exactly equal to the threshold serves a user;
- a threshold of `0.0` accepts any existing positive-weight edge;
- an absent edge does not serve a user even when the threshold is `0.0`;
- a sleeping RU does not serve a user; and
- an active RU with battery `0` does not serve a user.

Collector tests cover direct threshold validation and prove that QoS and
Network Lifetime both reflect the threshold through their shared service
observation. Factory tests verify that the configured threshold reaches both
service-based collectors and never reaches the battery-depletion collector.

## Scope Boundaries

This change does not alter connectivity graph membership or edge weights,
controller selection, battery consumption, metric timestamps, result types,
or output formatting. It adds no dependencies and no global configuration.
