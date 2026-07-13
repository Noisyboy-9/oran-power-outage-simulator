# Domain Models Design

## Goal

Implement the simulator's first domain objects: a Cartesian point, a user
identity, and a radio unit whose battery decreases according to its current
operating status.

## Components

### Point

`Point` is an immutable dataclass with `x: float` and `y: float` coordinates.
It exposes `distance_to(other: Point) -> float`, which returns the Euclidean
Cartesian distance between the two points.

### User

`User` is an immutable dataclass containing `id: int`. No location, behavior,
or other user state is introduced in this phase.

### Radio Unit

`RUStatus` is an enum containing exactly two states:

- `SLEEP = "sleep"`
- `ACTIVE = "active"`

`RU` is a mutable dataclass containing:

- `id: int`
- `battery: float`
- `status: RUStatus`
- `active_consumption: float`
- `sleep_consumption: float`

The consumption values are runtime configuration supplied to each RU when it
is constructed. Keeping them on the RU permits different units to have
different consumption characteristics without passing configuration into
every battery update or introducing a separate configuration abstraction.

## Battery Update

`RU.update_battery(delta_time: float = 1.0) -> None` mutates the RU's battery.
It uses `active_consumption` when the status is `RUStatus.ACTIVE` and
`sleep_consumption` when the status is `RUStatus.SLEEP`. The update implements:

```text
battery = max(0, battery - delta_time * selected_consumption)
```

This is equivalent to the supplied formula, with active status represented by
`x_r(t) = 1` and sleep status represented by `x_r(t) = 0`. The default timestep
is one. The method returns `None`; callers read the updated `ru.battery` state.

## Public Imports

The `simulator.domain` package re-exports `Point`, `User`, `RU`, and `RUStatus`
so callers do not need to depend on the domain package's file layout.

## Validation and Errors

This phase does not define validation behavior for coordinates, identifiers,
battery levels, consumption rates, or timestep values. The objects apply the
supplied typed values directly. Validation can be added later if the simulator
defines domain constraints and required failure behavior.

## Testing

Tests mirror the source modules under `tests/domain/` and verify externally
visible behavior:

- a known Cartesian distance and zero distance between identical points;
- integer user ID storage and value equality;
- the exact active and sleep enum states;
- active battery consumption with the default one-unit timestep;
- sleep battery consumption with a custom timestep;
- battery clamping at zero; and
- in-place battery mutation with a `None` return value.

Tests remain deterministic and use `pytest.approx` where floating-point
comparisons require tolerance.

## Scope Boundaries

This design does not add positions to users or RUs, RU controller behavior,
environment ownership, simulation timing orchestration, metrics, additional RU
statuses, shared configuration objects, persistence, or validation rules.
