# RU Controllers Design

## Goal

Implement three radio-unit control policies that receive the current RU list and
timestamp, then prepare RU statuses for that timestamp. The work also
encapsulates mutable RU battery and status state so controllers interact with
RUs through explicit methods.

## RU State Encapsulation

`RU` keeps its existing constructor signature:

```python
RU(
    id: int,
    battery: float,
    status: RUStatus,
    active_consumption: float,
    sleep_consumption: float,
)
```

The constructor stores the current battery, initial capacity, and current status
in private `_battery`, `_initial_capacity`, and `_status` fields. The initial
capacity is the constructor's battery value and never changes.

RU exposes these methods:

```python
get_battery() -> float
get_initial_capacity() -> float
get_status() -> RUStatus
set_status(status: RUStatus) -> None
update_battery(delta_time: float = 1.0) -> None
```

There is no public battery setter. Battery changes only through
`update_battery()`, which retains the existing consumption behavior and clamps
the current battery at zero. The initial battery, active consumption, and sleep
consumption must remain strictly positive at construction, while depletion may
reduce current battery to zero. The constructor and `set_status()` reject values
that are not `RUStatus` members with `DomainValidationError`.

## Controller Interface

`RUController` is an abstract base class with one operation:

```python
update(rus: list[RU], timestamp: int) -> None
```

Every controller receives the RUs on each call, mutates their statuses in place,
and returns `None`. Controllers do not own the environment, retain the RU list,
or consume battery. They may read RU IDs and consumption rates directly and use
the RU access methods for battery and status state.

`AlwaysActiveController`, `StaggeredActiveController`, and
`ThresholdStaggeredActiveController` implement this interface independently.
They may use small shared helpers, but policy classes do not inherit behavior
from one another.

Controller timestamps must be non-negative integers. Invalid timestamps raise
`ValueError`. Passing an empty RU list is a valid no-op for every controller.

## Activation Eligibility

An RU has enough battery to be active for the next timestamp when:

```text
current battery >= active consumption
```

Whenever a policy selects an RU for activation and this condition is false, the
controller explicitly sets that RU to `SLEEP`. This prevents an ineligible RU
from retaining a previous `ACTIVE` status.

## Always-Active Policy

`AlwaysActiveController` selects every RU on every call. Eligible RUs become
`ACTIVE`; ineligible RUs become `SLEEP`. The timestamp is validated and accepted
for interface consistency but otherwise does not affect this policy.

## Staggered Policy

`StaggeredActiveController` selects an ID-parity group from the global timestamp:

- timestamps `0` through `9`: even-ID RUs;
- timestamps `10` through `19`: odd-ID RUs;
- timestamps `20` through `29`: even-ID RUs; and
- subsequent groups continue alternating every ten timestamps.

This is equivalent to selecting even IDs when `(timestamp // 10) % 2 == 0` and
odd IDs otherwise. Selected and eligible RUs become `ACTIVE`. Selected but
ineligible RUs become `SLEEP` and emit the informational log described below.
All non-selected RUs become `SLEEP` without a log.

## Threshold-Staggered Policy

`ThresholdStaggeredActiveController` receives `threshold_percentage: float` in
its constructor. The threshold must be between `0` and `100`, inclusive;
otherwise construction raises `ValueError`.

The controller begins in all-active mode. It switches to staggered mode on the
first non-empty update where every RU satisfies:

```text
current battery / initial capacity * 100 <= threshold percentage
```

The transition is permanent. Staggering uses the global timestamp groups and
does not restart its ten-timestamp cycle when the threshold is reached. Thus, a
transition at timestamp 37 immediately selects the odd-ID group because
timestamps 30 through 39 form an odd-group interval.

Before the transition, every RU is selected using the same eligibility rule as
the always-active policy. An ineligible RU becomes `SLEEP` and emits an
informational log. After the transition, selected and non-selected RUs follow
the staggered policy. An empty RU list does not trigger the transition.

## Logging

The staggered and threshold-staggered modules use Python's standard-library
`logging` package with module-level loggers. No logging dependency or
configuration abstraction is introduced.

When either controller selects an RU but cannot activate it because its battery
is below active consumption, it emits an `INFO` record containing:

- the controller name;
- RU ID;
- timestamp;
- remaining battery; and
- required active consumption.

The threshold controller emits the same record for ineligible RUs during its
initial all-active phase. Non-selected RUs do not produce this record. The
always-active controller remains silent when an RU is ineligible.

## Public Imports

The `simulator.controllers` package re-exports the abstract interface and all
three concrete controller classes. Existing domain exports remain available.

## Testing

Tests mirror the controller modules under `tests/controllers/` and verify
externally visible behavior:

- RU battery and status access through the explicit methods;
- fixed initial capacity and unchanged active/sleep battery depletion;
- rejection of invalid constructor and setter statuses;
- always-active eligibility below, at, and above active consumption;
- staggered parity behavior and boundaries at timestamps 9, 10, 19, and 20;
- forced sleep and `INFO` logging for selected but ineligible RUs;
- silence for non-selected RUs and always-active ineligibility;
- threshold percentage equality and the requirement that every RU cross it;
- the threshold policy's permanent one-way transition;
- use of the global timestamp cycle after the threshold transition;
- valid empty RU lists; and
- rejection of invalid timestamps and threshold percentages.

Tests use deterministic RU values and pytest log capture. The complete pytest,
Ruff lint, and Ruff formatting checks must pass.

## Scope Boundaries

This change does not implement the environment or simulation controller,
consume battery from a controller, define configuration-file loading, add a
high-performance logging system, add battery charging or replacement, or add
new RU statuses. Simulation duration configuration remains future orchestration
work; controllers only act on timestamps supplied by their caller.
