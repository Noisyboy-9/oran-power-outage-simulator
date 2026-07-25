# Simulation Orchestration Design

## Goal

Make `Simulation` the entry point for one configured simulation. It owns the
simulation timestamp and coordinates environment state updates, RU policy
updates, and metric collection.

## Construction

The YAML configuration has a required top-level `simulation` section:

```yaml
simulation:
  steps: 10000
```

The loader parses it into `SimulationConfig(steps: int)`. `steps` must be a
positive integer; zero, negative, boolean, and non-integer values are rejected
with the same path-aware configuration errors used by the existing schema.

`Simulation(config: ApplicationConfig, metric_collectors: Iterable[MetricCollector] = ())`
builds the configured `RUController`, passes it to
`Environment(config.environment, controller)`, and owns the timestamp, which
starts at `0`.

Configuration loading, logging setup, collector construction, and command-line
argument handling belong to a future `main.py`. It will load an
`ApplicationConfig`, create the desired collectors, and pass both into
`Simulation`.

There are no concrete metric collectors or metric configuration entries yet.
Consequently, the default collector list is empty. Optional collector instances
let the future application composition root register collector implementations
without giving them control of the environment or simulation flow.

## Running the Simulation

`simulate()` is the public simulation entry point. It calls the private
`_step()` method exactly `config.simulation.steps` times. After it returns, the
timestamp therefore equals the configured step count.

`_step()` advances the timestamp by one, calls
`environment.update(timestamp)`, and then calls each metric collector.
`Environment.update(timestamp)` performs these operations in order:

1. Update every RU battery using its status from the preceding timestamp.
2. Give the full RU list and new timestamp to the configured `RUController`.
3. Rebuild the connectivity graph for the resulting step state.
4. Call `collect(environment)` on each registered `MetricCollector`.

Battery depletion happens before policy selection so a policy uses the current,
post-depletion battery state to choose statuses for the next timestamp.

## Component Boundaries

`Environment` owns the `RUController` as part of its mutable simulation state.
It exposes `update(timestamp)` because it owns the RU collection, controller,
and connectivity graph. `Simulation` retains responsibility only for advancing
global time and collecting metrics after environment state updates.

`RUController.update(rus, timestamp) -> list[RU]` updates statuses and returns
the RU list to be adopted by the environment. Controllers must return the same
RU instances supplied to them; they do not create replacement RUs. The
environment exposes `set_rus(rus)` to make that ownership handoff explicit
and adopts a shallow copy of the supplied list without validation. The
environment and RU
controllers are a trusted boundary: controllers are responsible for returning
a compatible list containing the existing RU instances, as documented on the
`RUController` interface. This preserves the map occupancy and location
indexes, which are keyed by RU identity, while allowing the simulation
controller to pass the policy result back to the environment. `set_rus` keeps
a copy of the list so callers cannot later alter the environment's collection
structure through the list reference they passed; the RU objects themselves
remain shared, retaining their updated statuses.

`MetricCollector` is an abstract interface with
`collect(environment: Environment) -> None`. Collectors observe the environment
after all step-state updates and must not control the simulation.

`Simulation` exposes read-only `timestamp` and `environment` properties. They
provide the small observable surface needed by callers and integration tests,
without exposing the single-step operation as public API.

## Testing

Configuration tests verify the new `simulation.steps` schema and its positive
integer validation. Simulation tests use small, real `ApplicationConfig`
objects and the existing real RU controllers. They verify construction,
`simulate()` running exactly its configured number of iterations, battery
depletion before controller status selection, repeated-step behavior, and
metric collection after all state updates. A test-only recording collector
records the observed environment state; it is used only to prove the public
observer contract and ordering. Environment battery and connectivity operations
also receive focused tests.

Controller and environment tests verify that every controller returns its input
RU list, `set_rus` adopts the supplied list, and `Environment.update()` runs
the complete ordered state lifecycle. Simulation tests verify that it delegates
the update to the environment before collecting metrics. Existing environment
getters remain public and unchanged.

## Scope Boundaries

This change does not add concrete metrics, metric configuration, a CLI or
`main.py`, mobility, or connectivity formulas that depend on RU status. The
existing graph construction formula is simply rerun each step.
