# Simulator Scaffold Design

## Goal

Create a lean, high-quality Python 3.12 project scaffold for a custom dependable-networking simulator. The project directory and import package are both named `simulator`. This phase establishes structure and tooling only; it does not implement simulation behavior.

## Tooling

- Python 3.12 is the minimum and selected development version.
- `uv` manages the virtual environment, dependencies, commands, and lockfile.
- `pyproject.toml` contains standard project metadata and configuration.
- Pytest provides the future test framework.
- Ruff provides future linting and formatting.
- The package uses a `src` layout to prevent accidental imports from the repository root.

## Project Structure

```text
simulator/
├── .gitignore
├── .python-version
├── README.md
├── pyproject.toml
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-07-13-simulator-scaffold-design.md
├── src/
│   └── simulator/
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── point.py
│       │   ├── ru.py
│       │   └── user.py
│       ├── controllers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── always_active.py
│       │   ├── staggered_active.py
│       │   └── threshold_staggered_active.py
│       ├── metrics/
│       │   ├── __init__.py
│       │   └── base.py
│       ├── environment.py
│       └── simulation_controller.py
└── tests/
    ├── controllers/
    ├── domain/
    ├── metrics/
    ├── test_environment.py
    └── test_simulation_controller.py
```

Empty `.gitkeep` files retain test subdirectories until tests are implemented. Empty `__init__.py` files identify Python packages. All other Python modules remain empty during scaffolding.

## Responsibilities

- `domain` contains the simulation's basic data concepts: `Point`, `RU`, and `User`.
- `controllers` contains the RU-controller abstraction and the always-active, staggered-active, and threshold-triggered staggered policies.
- `metrics` contains the metric-collector abstraction. Specific collectors will be added as separate focused modules later.
- `environment.py` will represent and own the complete simulation state.
- `simulation_controller.py` will coordinate time steps, RU policies, environment updates, and metric collection.

## Dependency Direction

Domain objects remain independent. RU controllers may depend on domain objects. Metric collectors may observe the environment but do not control it. The environment owns entities and state. The simulation controller is the orchestration boundary and may depend on all other parts.

## Runtime Flow

Once implemented, each simulation step will be initiated by the simulation controller. It will evaluate RU controllers, update the environment, and then invoke each registered metric collector against the resulting step state. The scaffold defines locations for these responsibilities without prescribing their future method signatures.

## Error Handling and Testing

No runtime error handling is needed in this scaffolding phase because there is no executable simulation behavior. Future unit tests will mirror the package boundaries under `tests/`. The initial verification checks that uv can create and synchronize the Python 3.12 environment, import the `simulator` package, expose pytest, and lint the empty scaffold successfully. Executing pytest is deferred until the project contains its first test because pytest treats an empty suite as a nonzero exit.

## Scope Boundaries

This phase does not define class attributes, constructors, algorithms, controller timing behavior, metric formulas, command-line interfaces, configuration formats, persistence, or visualization. Those decisions belong to later feature designs.
