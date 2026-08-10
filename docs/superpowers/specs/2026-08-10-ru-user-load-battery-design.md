# RU User-Load Battery Consumption Design

## Goal

Make an RU's per-step battery depletion depend on its active status and the
number of users it is servicing. An inactive RU continues to use its existing
sleep consumption. An active RU uses a distinct configured rate when it serves
zero or one user, and a configured per-user coefficient when it serves two or
more users.

For this feature, an RU services a user when the current connectivity graph
contains an RU-user edge whose weight is greater than or equal to the configured
`minimum_service_link_weight`. The model deliberately does not assign a user to
one exclusive RU, so a qualifying user can contribute to the load of more than
one active RU.

## Configuration

Replace the RU configuration field `active_consumption` with these required,
positive numeric fields:

- `zero_user_consumption`;
- `one_user_consumption`; and
- `multi_user_consumption_per_user`.

`sleep_consumption` remains required and positive. `RUConfig`, YAML loading,
and all direct configuration fixtures use the new field names; the legacy
`active_consumption` key is rejected rather than retained for compatibility.

The default configuration values are:

```yaml
environment:
  ru:
    count: 5
    initial_battery: 100.0
    initial_status: active
    zero_user_consumption: 1.0
    one_user_consumption: 2.0
    multi_user_consumption_per_user: 1.5
    sleep_consumption: 0.5
    coverage_radius: 8.0
```

They express a base operating cost for an idle active RU, preserve the former
`2.0` active cost for one serviced user, and grow the multi-user cost linearly.

## Battery Depletion

`RU` owns the consumption calculation and battery mutation. Its constructor
stores the three active-load rates as public read-only-by-convention attributes,
alongside the existing sleep rate. `update_battery()` retains its
`delta_time: float = 1.0` argument and gains a keyword-friendly
`serviced_user_count: int = 0` argument. The count must be a non-boolean,
non-negative integer; invalid values raise `DomainValidationError`.

For one call to `update_battery()`, consumption is:

| RU status | Qualifying serviced-user count | Consumption |
| --- | ---: | --- |
| `SLEEP` | any | `sleep_consumption` |
| `ACTIVE` | 0 | `zero_user_consumption` |
| `ACTIVE` | 1 | `one_user_consumption` |
| `ACTIVE` | 2 or more | `serviced_user_count * multi_user_consumption_per_user` |

The battery remains clamped to `0.0`. The supplied count does not affect a
sleeping RU.

## Step Integration and Timing

`Simulation._step()` passes
`config.simulation.metrics.minimum_service_link_weight` to
`Environment.update()` for every timestamp. `Environment.update()` passes that
threshold to its battery-update phase.

Before the graph is rebuilt, the environment examines the current graph for
each RU. It counts incident user edges with `weight >= minimum_service_link_weight`
and passes that count to `ru.update_battery(serviced_user_count=...)`. The graph
and RU statuses at the start of the update therefore describe the just-completed
timestep whose energy is being charged. After batteries are charged, controller
selection runs, then the connectivity graph is rebuilt, preserving the existing
step order.

The threshold has a single configuration source in `simulation.metrics`; it is
not duplicated or moved into `EnvironmentConfig`. Environment code does not
import metric collectors or their private helpers.

## Controller Eligibility

The controller activation check changes from `battery >= active_consumption` to
`battery >= zero_user_consumption`. This minimum-cost rule permits an RU to
activate whenever it can afford at least an idle active timestep. It does not
attempt to predict the next graph's served-user count.

An active RU that is busy enough to exhaust its battery during the next charge
is clamped to zero; the controller runs immediately afterward and changes it to
sleep because it no longer meets the minimum-cost threshold. Staggered selection
and threshold-staggering behavior otherwise remain unchanged. The existing
activation-failure event continues to report `required_battery`, now equal to
`zero_user_consumption`.

## Testing

Tests will prove the observable behavior at each boundary:

- RU tests cover sleep consumption regardless of supplied count; active zero-,
  one-, and multi-user consumption; exact multi-user multiplication; battery
  clamping; and invalid serviced-user counts.
- Environment tests set controlled graph-edge weights and verify that only
  edges at or above the supplied threshold contribute to the active RU's
  battery depletion, including equality at the threshold and no qualifying
  edges.
- Simulation tests verify that its configured service-link threshold reaches
  `Environment.update()` on every step.
- Controller tests verify that `zero_user_consumption` is the activation
  boundary and the logged required battery for an ineligible selected RU.
- Configuration tests verify construction and YAML loading with all new fields,
  reject absent or unknown active-consumption fields, and retain positive-number
  validation.

The full test suite, Ruff lint check, and Ruff format check are required before
completion. The README will describe the new RU configuration and timing
semantics.

## Scope Boundaries

This change does not add a user-to-RU assignment algorithm, alter connectivity
generation or weights, change metric definitions, change controller scheduling,
or introduce new dependencies. It does not make battery consumption depend on
metric collector selection; only the configured service-link threshold is
reused.
