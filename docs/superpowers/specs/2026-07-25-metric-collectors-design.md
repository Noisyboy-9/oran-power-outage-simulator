# Metric Collectors Design

## Goal

Implement three independent metric collectors for a configured simulation:

- Average Emergency QoS;
- Average RU Battery Depletion Time; and
- Network Lifetime.

Collectors observe, but never modify, the environment. Configuration chooses
which collectors run, `Simulation` provides a complete time-indexed observation
stream, and `main.py` constructs collectors and retrieves their final results.

## Configuration

The required simulation configuration gains a required `metrics` mapping:

```yaml
simulation:
  steps: 10000
  metrics:
    collectors:
      - average_emergency_qos
      - average_ru_battery_depletion_time
      - network_lifetime
    minimum_emergency_service_fraction: 0.8
```

`SimulationConfig` owns a nested immutable `MetricsConfig` with:

```python
collectors: tuple[MetricKind, ...]
minimum_emergency_service_fraction: float
```

`MetricKind` is a string enum whose values are the three YAML collector names
shown above. The loader preserves collector order, rejects unknown or duplicate
names, requires a list of strings, and rejects unknown metrics keys. An empty
collector list is valid. `minimum_emergency_service_fraction` is always
required and must be a non-boolean number in `(0, 1]`, even when network
lifetime is not selected; this keeps the metrics section uniform and fully
validated.

## Collector Contract

`MetricCollector` remains an abstract observer, extended with the following
public contract:

```python
name: str

collect(environment: Environment, timestamp: int) -> None
finish_calculation() -> float
```

Every concrete collector has a stable `name` matching its `MetricKind` value.
`collect()` receives the completed environment state and its explicit
simulation timestamp. It does not mutate the environment. Each collector
requires an uninterrupted observation sequence beginning at `t=0`: timestamps
must be non-boolean integers and must be exactly the next expected timestamp.
Duplicate, out-of-order, skipped, and negative timestamps raise `ValueError`.
This makes a missing measurement explicit instead of silently calculating a
metric over a misleading horizon.

`finish_calculation()` raises `ValueError` when called before an observation.
All configured simulations have at least the initial `t=0` observation, so
this protects direct collector use without affecting normal runs.

Each collector retains its metric-relevant observations indexed by timestamp.
This makes the result auditable and supports future reporting without giving
the collector responsibility for simulation control or output formatting.

## Observation Lifecycle

`Simulation` is responsible for the complete observation sequence:

1. At the start of the first `simulate()` call, call every collector with the
   initial environment and timestamp `0`.
2. For each configured step, increment the timestamp, update the environment,
   then call every collector with the resulting environment and timestamp.

The initial observation is collected exactly once, even if `simulate()` is
called again on the same instance. A concise comment next to this call explains
that the initial collection preserves the problem statement's `t=0` through
`T-1` metric horizon; it is not an environment update.

`main.py` remains the composition root. It creates the selected collectors from
`config.simulation.metrics.collectors`, passes them to `Simulation`, and, after
`simulate()` returns, calls `finish_calculation()` exactly once on each one.
Collector-name mapping belongs in a focused metrics factory used by `main.py`,
not in `Simulation`.

## Shared Service Observation

Average Emergency QoS and Network Lifetime use one small private metrics helper
to calculate the served-user fraction for one environment state. A user is
served when it has an edge to at least one RU whose status is `ACTIVE`; multiple
active connections still count only once. The connection's random weight is
irrelevant once an edge exists. Sleeping RUs and users with no active connected
RU do not contribute to the fraction.

The helper returns a value in `[0.0, 1.0]`. Environment configuration guarantees
at least one user, so division by zero is not a simulation case.

## Concrete Collectors

### Average Emergency QoS

At every timestamp, record the served-user fraction. The final value is the
arithmetic mean of all recorded fractions, including the initial observation.

### Average RU Battery Depletion Time

At every timestamp, record each RU's battery by RU ID. For every RU, find the
first timestamp whose recorded battery is `<= 0`. Its depletion time is that
timestamp. An RU without a zero-battery observation has depletion time
`float("inf")`; consequently, if any RU survives the observed horizon, the
average depletion time is infinity. This is intentional: a finite simulation
cannot claim a finite depletion time that it did not observe.

### Network Lifetime

At every timestamp, record the served-user fraction. Given the configured SLA
fraction alpha:

- if the fraction is below alpha at `t=0`, the lifetime is `0`;
- at the first later timestamp `t` below alpha, the lifetime is `t - 1`;
- once a violation occurs, a later recovery does not change the result; and
- if no recorded timestamp violates the SLA, the lifetime is `float("inf")`.

Equality with alpha satisfies the SLA.

## Testing

Tests mirror the source and configuration boundaries.

- Verify the abstract collector contract and stable concrete collector names.
- Verify timestamp validation for boolean, negative, duplicate, out-of-order,
  and skipped timestamps, plus finalization before collection.
- Use small deterministic fake environments to test collector logic without
  placement or random graph weights obscuring the assertions.
- Verify collection leaves RU status, battery, users, and connectivity
  unchanged.
- Verify QoS for no, complete, and partial service; an active connected RU;
  sleeping connected RUs; disconnected users; and multiple active RUs serving
  the same user exactly once.
- Verify QoS averaging across `t=0` and later observations.
- Verify battery histories, exact-zero and later depletion, first-depletion
  preservation, finite averages, and infinity when one or all RUs do not
  deplete.
- Verify network lifetime at the alpha boundary, violation at `t=0`, violation
  after successful observations, no extension after recovery, and infinity
  when the SLA is never violated.
- Verify metrics configuration loading, ordering, empty collector lists,
  unknown and duplicate names, invalid list entries, invalid alpha values, and
  unknown metrics keys.
- Verify the simulation calls collectors at `t=0` before the first update and
  after every update, without duplicating `t=0` on a later `simulate()` call.
- Verify `main.py` builds the requested collectors and finalizes each one once
  after simulation completion.

## Scope Boundaries

This work does not alter RU policy behavior, environment connectivity rules,
simulation step count, persistence, CLI arguments, or output formatting. It
adds no global metric registry and no generic reporting framework.
