# Simulator

A custom dependable-networking simulator built with Python 3.12.

The repository currently implements the core `Point`, `User`, and `RU` domain
models. RU control policies, orchestration behavior, and metric calculations
remain scaffolded for later phases.

## Domain Models

- `Point` represents non-negative Cartesian coordinates and calculates distance
  to another point.
- `User` represents a simulation user with a positive integer ID.
- `RU` represents a radio unit with a positive integer ID, battery state,
  active or sleep status, configured consumption rates, and status-based
  battery depletion.
- Invalid constructor values raise `DomainValidationError`.

## Setup

Install [uv](https://docs.astral.sh/uv/), then synchronize the development environment:

```bash
uv sync --dev
```

Run project tools through uv:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Structure

- `src/simulator/domain`: core simulation objects (`Point`, `RU`, and `User`)
- `src/simulator/controllers`: the RU-controller abstraction and policies
- `src/simulator/metrics`: the metric-collector abstraction and future collectors
- `src/simulator/environment.py`: the complete simulation environment
- `src/simulator/simulation_controller.py`: time-step orchestration
- `tests`: tests organized to mirror the source package
