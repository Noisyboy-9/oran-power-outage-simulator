# Domain Models Design

## Goal

Implement the simulator's first domain objects: a Cartesian point, a user
identity, and a radio unit whose battery decreases according to its current
operating status.

## Components

### Point

`Point` is an immutable dataclass with `x: float` and `y: float` coordinates.
It exposes `distance_to(other: Point) -> float`, which returns the Euclidean
Cartesian distance between the two points. Both coordinates must be
non-negative, so zero is valid but a negative coordinate is rejected.

### User

`User` is an immutable dataclass containing `id: int`. The ID must be strictly
positive. No location, behavior, or other user state is introduced in this
phase.

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
The ID, initial battery, active consumption, and sleep consumption must all be
strictly positive. Battery depletion may still reduce the battery to zero
after successful construction.

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

The `simulator.domain` package re-exports `Point`, `User`, `RU`, `RUStatus`, and
`DomainValidationError` so callers do not need to depend on the domain
package's file layout.

## Validation and Errors

`DomainValidationError` is a custom domain exception that subclasses
`ValueError`. Constructors raise it with a message naming the invalid field
when any of these constraints fail:

- `Point.x` and `Point.y` must each be greater than or equal to zero;
- `User.id` must be greater than zero; and
- `RU.id`, initial `RU.battery`, `RU.active_consumption`, and
  `RU.sleep_consumption` must each be greater than zero.

Timestep validation is outside this phase because no constraint for
`delta_time` has been defined.

## Testing

Tests mirror the source modules under `tests/domain/` and verify externally
visible behavior:

- a known Cartesian distance and zero distance between identical points;
- valid zero point coordinates and rejection of each negative coordinate;
- integer user ID storage and value equality;
- rejection of non-positive user IDs;
- the exact active and sleep enum states;
- active battery consumption with the default one-unit timestep;
- sleep battery consumption with a custom timestep;
- battery clamping at zero;
- in-place battery mutation with a `None` return value; and
- rejection of each non-positive RU constructor field.

Tests remain deterministic and use `pytest.approx` where floating-point
comparisons require tolerance.

## Scope Boundaries

This design does not add positions to users or RUs, RU controller behavior,
environment ownership, simulation timing orchestration, metrics, additional RU
statuses, shared configuration objects, persistence, or timestep validation.
