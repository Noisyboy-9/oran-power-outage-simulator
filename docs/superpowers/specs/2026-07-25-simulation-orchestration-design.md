# Simulation Orchestration Design

## Goal

Make `Simulation` the entry point for one configured simulation. It owns the
simulation timestamp and coordinates environment state updates, RU policy
updates, and metric collection.

## Construction

`Simulation(config: ApplicationConfig, metric_collectors: Iterable[MetricCollector] = ())`
creates its `Environment` and `RUController` from the supplied configuration's
environment and controller branches. The timestamp starts at `0`.

Configuration loading, logging setup, collector construction, and command-line
argument handling belong to a future `main.py`. It will load an
`ApplicationConfig`, create the desired collectors, and pass both into
`Simulation`.

There are no concrete metric collectors or metric configuration entries yet.
Consequently, the default collector list is empty. Optional collector instances
let the future application composition root register collector implementations
without giving them control of the environment or simulation flow.

## One Step

`step()` advances the timestamp by one and performs these operations in order:

1. Update every RU battery using its status from the preceding timestamp.
2. Give the full RU list and new timestamp to the configured `RUController`.
3. Rebuild the connectivity graph for the resulting step state.
4. Call `collect(environment)` on each registered `MetricCollector`.

Battery depletion happens before policy selection so a policy uses the current,
post-depletion battery state to choose statuses for the next timestamp.

## Component Boundaries

`Environment` remains independent of controllers. It exposes focused
`update_batteries()` and `update_connectivity_graph()` operations because it
owns the RU collection and graph. `Simulation` retains responsibility for the
order in which the environment and RU controller run.

`MetricCollector` is an abstract interface with
`collect(environment: Environment) -> None`. Collectors observe the environment
after all step-state updates and must not control the simulation.

`Simulation` exposes read-only `timestamp` and `environment` properties. They
provide the small observable surface needed by callers and integration tests,
without exposing mutable orchestration state.

## Testing

Simulation tests use small, real `ApplicationConfig` objects and the existing
real RU controllers. They verify construction, the timestamp increment,
battery depletion before controller status selection, repeated-step behavior,
and metric collection after all state updates. A test-only recording collector
records the observed environment state; it is used only to prove the public
observer contract and ordering. Environment battery and connectivity operations
also receive focused tests.

## Scope Boundaries

This change does not add concrete metrics, metric configuration, a simulation
duration, a CLI or `main.py`, mobility, or connectivity formulas that depend on
RU status. The existing graph construction formula is simply rerun each step.
