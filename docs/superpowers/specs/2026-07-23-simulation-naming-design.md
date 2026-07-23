# Simulation Naming Design

## Goal

Remove the conceptual ambiguity between the top-level simulation orchestrator
and the RU state-control policies.

## Decision

Rename the empty orchestration module from `simulation_controller.py` to
`simulation.py`. Its future public orchestration object will be named
`Simulation` rather than `SimulationController`.

The `simulator.controllers` package and the `RUController` interface retain
their names. They accurately describe policies that set RU states and remain
separate from simulation-wide orchestration.

## Scope

This is a naming-only scaffold refactor. It renames the empty source and test
modules and updates current project documentation. It does not add a
`Simulation` class, define its methods, or introduce any runtime behavior.

## Documentation

The root architecture references use `src/simulator/simulation.py` and call it
the simulation orchestration boundary. Historical design and implementation
plan documents are preserved as records of earlier work.
