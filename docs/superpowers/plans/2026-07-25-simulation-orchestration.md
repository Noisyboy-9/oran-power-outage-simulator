# Simulation Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `Simulation` as the configuration-driven owner of a deterministic simulation timestep.

**Architecture:** The future application composition root supplies an already-loaded `ApplicationConfig` and zero or more metric collectors. `Simulation` creates the environment and RU controller, owns the timestamp, and coordinates battery updates, policy application, graph rebuilding, and observation in that exact order. The environment retains ownership of mutable state, while collectors remain read-only observers by contract.

**Tech Stack:** Python 3.12, pytest, Ruff, NetworkX, PyYAML.

## Global Constraints

- Python version floor: `>=3.12`.
- Do not add a `main.py`, metric configuration, concrete metrics, simulation duration, mobility, or status-dependent connectivity behavior.
- `Simulation` accepts `ApplicationConfig` plus an optional iterable of `MetricCollector` instances; it does not read YAML files.
- A step increments the timestamp, updates batteries using prior statuses, applies the RU controller, rebuilds the graph, then collects metrics.
- Preserve existing public APIs and keep domain objects independent of orchestration.
- Use `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .` for verification.

---

## File Structure

- `src/simulator/metrics/base.py`: defines the abstract metric-observer contract.
- `src/simulator/metrics/__init__.py`: exposes the public metric interface.
- `src/simulator/environment/environment.py`: adds state-owner operations for battery and graph updates.
- `src/simulator/simulation.py`: defines the public orchestration controller.
- `tests/metrics/test_base.py`: verifies the metric interface cannot be instantiated directly.
- `tests/environment/test_environment.py`: verifies environment battery updates.
- `tests/environment/test_connectivity.py`: verifies graph rebuilding is externally observable.
- `tests/test_simulation.py`: verifies construction, step ordering, repeated steps, and collector timing through public behavior.
- `README.md`: documents the implemented orchestration boundary and usage.

### Task 1: Metric collector interface

**Files:**
- Modify: `src/simulator/metrics/base.py`
- Modify: `src/simulator/metrics/__init__.py`
- Test: `tests/metrics/test_base.py`

**Interfaces:**
- Consumes: `Environment` from `simulator.environment`.
- Produces: `MetricCollector.collect(self, environment: Environment) -> None` and public import `from simulator.metrics import MetricCollector`.

- [ ] **Step 1: Write the failing interface test**

```python
import pytest

from simulator.metrics import MetricCollector


def test_metric_collector_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        MetricCollector()
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/metrics/test_base.py -v`

Expected: FAIL because `MetricCollector` is not publicly importable.

- [ ] **Step 3: Implement the minimal abstract contract**

```python
from abc import ABC, abstractmethod

from simulator.environment import Environment


class MetricCollector(ABC):
    @abstractmethod
    def collect(self, environment: Environment) -> None:
        """Observe the environment after a simulation step."""
```

Export `MetricCollector` from `simulator.metrics` using `__all__`.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `uv run pytest tests/metrics/test_base.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the interface change**

```bash
git add src/simulator/metrics/base.py src/simulator/metrics/__init__.py tests/metrics/test_base.py
git commit -m "feat: add metric collector interface"
```

### Task 2: Environment timestep operations

**Files:**
- Modify: `src/simulator/environment/environment.py`
- Modify: `tests/environment/test_environment.py`
- Modify: `tests/environment/test_connectivity.py`

**Interfaces:**
- Consumes: the environment-owned `RU` collection and existing `_create_connectivity_graph()` helper.
- Produces: `Environment.update_batteries(self) -> None` and `Environment.update_connectivity_graph(self) -> None`.

- [ ] **Step 1: Write failing battery-update tests**

Append this test using the existing `make_config` helper:

```python
def test_updates_all_ru_batteries_using_their_current_statuses() -> None:
    environment = Environment(make_config(ru_count=2, initial_status=RUStatus.ACTIVE))
    active_ru, sleeping_ru = environment.get_rus()
    sleeping_ru.set_status(RUStatus.SLEEP)

    environment.update_batteries()

    assert active_ru.get_battery() == 98.0
    assert sleeping_ru.get_battery() == 99.5
```

- [ ] **Step 2: Run the battery test to verify it fails**

Run: `uv run pytest tests/environment/test_environment.py::test_updates_all_ru_batteries_using_their_current_statuses -v`

Expected: FAIL with `AttributeError` because `update_batteries` does not exist.

- [ ] **Step 3: Implement the minimal battery operation**

```python
def update_batteries(self) -> None:
    for ru in self._rus:
        ru.update_battery()
```

- [ ] **Step 4: Run the battery test to verify it passes**

Run: `uv run pytest tests/environment/test_environment.py::test_updates_all_ru_batteries_using_their_current_statuses -v`

Expected: PASS.

- [ ] **Step 5: Write the failing graph-rebuild test**

Append this test using the existing `make_environment` and
`edge_weights_by_ids` helpers:

```python
def test_rebuilds_connectivity_graph() -> None:
    environment = make_environment(random_seed=7)
    initial_weights = edge_weights_by_ids(environment)

    environment.update_connectivity_graph()

    assert edge_weights_by_ids(environment) != initial_weights
```

- [ ] **Step 6: Run the graph test to verify it fails**

Run: `uv run pytest tests/environment/test_connectivity.py::test_rebuilds_connectivity_graph -v`

Expected: FAIL with `AttributeError` because `update_connectivity_graph` does not exist.

- [ ] **Step 7: Implement the minimal graph operation**

```python
def update_connectivity_graph(self) -> None:
    self._connectivity_graph = self._create_connectivity_graph()
```

- [ ] **Step 8: Run the focused environment tests to verify they pass**

Run: `uv run pytest tests/environment/test_environment.py tests/environment/test_connectivity.py -v`

Expected: PASS.

- [ ] **Step 9: Commit the environment operations**

```bash
git add src/simulator/environment/environment.py tests/environment/test_environment.py tests/environment/test_connectivity.py
git commit -m "feat: add environment timestep updates"
```

### Task 3: Simulation controller

**Files:**
- Modify: `src/simulator/simulation.py`
- Modify: `tests/test_simulation.py`

**Interfaces:**
- Consumes: `ApplicationConfig`, `build_controller`, `Environment`, and `MetricCollector`.
- Produces: `Simulation(config: ApplicationConfig, metric_collectors: Iterable[MetricCollector] = ())`, read-only `timestamp` and `environment` properties, and `step() -> None`.

- [ ] **Step 1: Write failing construction and step-order tests**

Define a `make_application_config` helper using an `ALWAYS_ACTIVE` controller,
one initially sleeping RU with battery `10.0`, active consumption `3.0`, sleep
consumption `1.0`, and a valid `LoggingConfig`. Define this test-only observer:

```python
class RecordingCollector(MetricCollector):
    def __init__(self) -> None:
        self.observations: list[tuple[float, RUStatus]] = []

    def collect(self, environment: Environment) -> None:
        ru = environment.get_rus()[0]
        self.observations.append((ru.get_battery(), ru.get_status()))
```

Then add the behavioral tests:

```python
def test_starts_at_timestamp_zero_with_a_configured_environment() -> None:
    simulation = Simulation(make_application_config())

    assert simulation.timestamp == 0
    assert len(simulation.environment.get_rus()) == 1
    assert len(simulation.environment.get_users()) == 1


def test_step_depletes_before_selecting_status_and_collects_afterwards() -> None:
    collector = RecordingCollector()
    simulation = Simulation(make_application_config(), [collector])

    simulation.step()

    ru = simulation.environment.get_rus()[0]
    assert simulation.timestamp == 1
    assert ru.get_battery() == 9.0
    assert ru.get_status() is RUStatus.ACTIVE
    assert collector.observations == [(9.0, RUStatus.ACTIVE)]


def test_later_steps_use_the_status_selected_by_the_previous_step() -> None:
    simulation = Simulation(make_application_config())

    simulation.step()
    simulation.step()

    assert simulation.environment.get_rus()[0].get_battery() == 6.0
```

- [ ] **Step 2: Run the simulation tests to verify they fail**

Run: `uv run pytest tests/test_simulation.py -v`

Expected: FAIL because `Simulation` is not defined.

- [ ] **Step 3: Implement the minimal orchestrator**

```python
class Simulation:
    def __init__(
        self,
        config: ApplicationConfig,
        metric_collectors: Iterable[MetricCollector] = (),
    ) -> None:
        self._environment = Environment(config.environment)
        self._controller = build_controller(config.controller)
        self._metric_collectors = list(metric_collectors)
        self._timestamp = 0

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    def environment(self) -> Environment:
        return self._environment

    def step(self) -> None:
        self._timestamp += 1
        self._environment.update_batteries()
        self._controller.update(self._environment.get_rus(), self._timestamp)
        self._environment.update_connectivity_graph()
        for metric_collector in self._metric_collectors:
            metric_collector.collect(self._environment)
```

- [ ] **Step 4: Run the simulation tests to verify they pass**

Run: `uv run pytest tests/test_simulation.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the simulation controller**

```bash
git add src/simulator/simulation.py tests/test_simulation.py
git commit -m "feat: add simulation controller"
```

### Task 4: Public documentation and full verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `Simulation` public constructor and step method from Task 3.
- Produces: accurate user-facing architecture and usage documentation.

- [ ] **Step 1: Update the README architecture and usage text**

Replace the statement that simulation orchestration is scaffolded. Add a
`Simulation` section explaining that callers load configuration and create
collectors, then pass both to `Simulation`; `step()` runs battery updates,
controller selection, graph rebuilding, and metrics in order. Use this usage
snippet:

```python
from simulator.configuration import load_config
from simulator.simulation import Simulation

config = load_config(Path("configs/default.yaml"))
simulation = Simulation(config)
simulation.step()
```

- [ ] **Step 2: Run all tests**

Run: `uv run pytest`

Expected: PASS with no failures.

- [ ] **Step 3: Run Ruff linting**

Run: `uv run ruff check .`

Expected: exit code `0`.

- [ ] **Step 4: Run Ruff format verification**

Run: `uv run ruff format --check .`

Expected: exit code `0`.

- [ ] **Step 5: Review the complete change set**

Run: `git status --short && git diff --check HEAD && git diff HEAD`

Expected: only the controller implementation, supporting interfaces, tests,
and README changes; no whitespace errors.

- [ ] **Step 6: Commit the documentation**

```bash
git add README.md
git commit -m "docs: describe simulation orchestration"
```
