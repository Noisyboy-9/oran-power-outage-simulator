# Simulation Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a configuration-driven `Simulation` entry point that runs exactly its configured number of deterministic steps.

**Architecture:** `ApplicationConfig` contains a validated `SimulationConfig` with a positive step count. `Simulation` receives the already-loaded configuration and optional metric collectors, creates and owns the `Environment` and RU controller, then `simulate()` coordinates exactly that many private ordered update cycles. The environment retains ownership of mutable entities and connectivity state; metric collectors only observe completed steps.

**Tech Stack:** Python 3.12, pytest, NetworkX, PyYAML, Ruff, uv.

## Global Constraints

- Target Python 3.12 or newer; add type hints to public interfaces.
- Keep domain objects independent of orchestration; controllers do not own the environment.
- Keep metric collectors observational; `collect(environment)` must not change simulation flow.
- Do not add concrete metrics, metric configuration, `main.py`, CLI parsing, mobility, or new dependencies.
- Run project commands from the repository root with `uv`.

---

## File Structure

- `src/simulator/configuration/models.py`: declares `SimulationConfig` and adds it to `ApplicationConfig`.
- `src/simulator/configuration/loader.py`: parses and validates the required top-level `simulation.steps` mapping.
- `src/simulator/configuration/__init__.py`: re-exports `SimulationConfig`.
- `configs/default.yaml`: supplies the tracked default simulation step count.
- `tests/configuration/test_models.py`: verifies `SimulationConfig` validation and immutability.
- `tests/configuration/test_loader.py`: verifies loading and path-aware rejection of invalid `simulation.steps` values.
- `src/simulator/metrics/base.py`: declares the public abstract `MetricCollector` interface.
- `src/simulator/metrics/__init__.py`: re-exports `MetricCollector`.
- `src/simulator/environment/environment.py`: owns public battery and connectivity update operations.
- `src/simulator/simulation.py`: owns configuration-derived construction, timestamp, public run coordination, and private ordered step coordination.
- `tests/metrics/test_base.py`: verifies the metric interface cannot be instantiated directly.
- `tests/environment/test_environment.py`: verifies battery updates for current RU statuses.
- `tests/environment/test_connectivity.py`: verifies graph rebuilding produces the next seeded graph state.
- `tests/test_simulation.py`: verifies construction, step ordering, and collector observations using real configuration and controller behavior.
- `README.md`: replaces the statement that orchestration is scaffolded with the implemented lifecycle and use example.

### Task 1: Add Validated Simulation Run Configuration

**Files:**
- Modify: `src/simulator/configuration/models.py`
- Modify: `src/simulator/configuration/loader.py`
- Modify: `src/simulator/configuration/__init__.py`
- Modify: `configs/default.yaml`
- Modify: `tests/configuration/test_models.py`
- Modify: `tests/configuration/test_loader.py`

**Interfaces:**
- Produces: immutable `SimulationConfig(steps: int)` that rejects booleans, non-integers, and values below `1` with `ValueError`.
- Produces: `ApplicationConfig.simulation: SimulationConfig`.
- Produces: a required top-level YAML mapping `simulation: {steps: <positive integer>}` parsed by `load_config`.
- Produces: `from simulator.configuration import SimulationConfig`.

- [ ] **Step 1: Write the failing model tests**

Append to `tests/configuration/test_models.py`:

```python
from simulator.configuration import SimulationConfig


def test_simulation_config_accepts_positive_steps() -> None:
    assert SimulationConfig(steps=10_000).steps == 10_000


@pytest.mark.parametrize("steps", [0, -1, True, 1.5, "10"])
def test_simulation_config_rejects_non_positive_or_non_integer_steps(
    steps: object,
) -> None:
    with pytest.raises(ValueError, match="steps"):
        SimulationConfig(steps=steps)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run model tests to verify they fail**

Run: `uv run pytest tests/configuration/test_models.py -v`

Expected: FAIL during collection because `SimulationConfig` is not exported.

- [ ] **Step 3: Implement the typed model and public export**

```python
@dataclass(frozen=True)
class SimulationConfig:
    steps: int

    def __post_init__(self) -> None:
        if isinstance(self.steps, bool) or not isinstance(self.steps, int) or self.steps <= 0:
            raise ValueError("steps must be a positive integer")
```

Add `simulation: SimulationConfig` to `ApplicationConfig`, and add
`SimulationConfig` to the imports and `__all__` list in
`src/simulator/configuration/__init__.py`.

- [ ] **Step 4: Run model tests to verify they pass**

Run: `uv run pytest tests/configuration/test_models.py -v`

Expected: PASS; only positive integers construct the immutable model.

- [ ] **Step 5: Write the failing loader tests**

Add this section to `VALID_YAML` in `tests/configuration/test_loader.py`:

```yaml
simulation:
  steps: 3
```

Then add:

```python
def test_loads_simulation_steps(tmp_path: Path) -> None:
    assert load_config(write_config(tmp_path, VALID_YAML)).simulation.steps == 3


@pytest.mark.parametrize("steps", ["0", "-1", "true", "1.5"])
def test_rejects_invalid_simulation_steps(tmp_path: Path, steps: str) -> None:
    contents = VALID_YAML.replace("steps: 3", f"steps: {steps}")

    with pytest.raises(ConfigurationError, match="simulation.steps"):
        load_config(write_config(tmp_path, contents))
```

- [ ] **Step 6: Run loader tests to verify they fail**

Run: `uv run pytest tests/configuration/test_loader.py -v`

Expected: FAIL because the current root-key validator rejects `simulation`.

- [ ] **Step 7: Implement YAML parsing and update the default config**

Change the root required-key set to include `simulation`, call a new
`_parse_simulation(raw_config["simulation"], "simulation")`, and pass its
result as `simulation=` when constructing `ApplicationConfig`.

```python
def _parse_simulation(value: object, path: str) -> SimulationConfig:
    raw_simulation = _require_mapping(value, path)
    _require_exact_keys(raw_simulation, {"steps"}, path)
    return _construct(
        SimulationConfig,
        path,
        steps=_require_positive_integer(raw_simulation["steps"], f"{path}.steps"),
    )
```

Add the following to `configs/default.yaml`:

```yaml
simulation:
  steps: 10000
```

- [ ] **Step 8: Run configuration tests to verify they pass**

Run: `uv run pytest tests/configuration -v`

Expected: PASS; valid YAML returns `config.simulation.steps`, and malformed step values report `simulation.steps`.

- [ ] **Step 9: Commit the simulation configuration**

```bash
git add configs/default.yaml src/simulator/configuration tests/configuration
git commit -m "feat: configure simulation run length"
```

### Task 2: Publish the Metric Collector Interface

**Files:**
- Create: `tests/metrics/test_base.py`
- Modify: `src/simulator/metrics/base.py`
- Modify: `src/simulator/metrics/__init__.py`

**Interfaces:**
- Produces: `class MetricCollector(ABC)` with `collect(self, environment: Environment) -> None` as an abstract method.
- Produces: `from simulator.metrics import MetricCollector` as the package-level import.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from simulator.metrics import MetricCollector


def test_metric_collector_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        MetricCollector()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/metrics/test_base.py -v`

Expected: FAIL during collection because `MetricCollector` is not exported.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/simulator/metrics/base.py
from abc import ABC, abstractmethod

from simulator.environment.environment import Environment


class MetricCollector(ABC):
    @abstractmethod
    def collect(self, environment: Environment) -> None:
        """Observe the environment after a simulation step."""
```

```python
# src/simulator/metrics/__init__.py
from simulator.metrics.base import MetricCollector

__all__ = ["MetricCollector"]
```

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `uv run pytest tests/metrics/test_base.py -v`

Expected: PASS; the abstract interface raises `TypeError` on direct construction.

- [ ] **Step 5: Commit the interface**

```bash
git add src/simulator/metrics tests/metrics/test_base.py
git commit -m "feat: add metric collector interface"
```

### Task 3: Give the Environment Its Step-State Operations

**Files:**
- Modify: `src/simulator/environment/environment.py`
- Modify: `tests/environment/test_environment.py`
- Modify: `tests/environment/test_connectivity.py`

**Interfaces:**
- Produces: `Environment.update_batteries() -> None`, which calls `update_battery()` exactly once on every owned RU.
- Produces: `Environment.update_connectivity_graph() -> None`, which replaces the internal graph with a fresh result of `_create_connectivity_graph()`.
- Consumes: the existing RU battery/status API and `_create_connectivity_graph()` implementation.

- [ ] **Step 1: Write the failing battery-update test**

Append this test to `tests/environment/test_environment.py`:

```python
def test_updates_each_ru_battery_using_its_current_status() -> None:
    environment = Environment(
        make_config(
            ru_count=2,
            user_count=1,
            initial_battery=10.0,
            active_consumption=2.0,
            sleep_consumption=0.5,
        )
    )
    active_ru, sleeping_ru = environment.get_rus()
    active_ru.set_status(RUStatus.ACTIVE)
    sleeping_ru.set_status(RUStatus.SLEEP)

    environment.update_batteries()

    assert active_ru.get_battery() == 8.0
    assert sleeping_ru.get_battery() == 9.5
```

- [ ] **Step 2: Run the battery test to verify it fails**

Run: `uv run pytest tests/environment/test_environment.py::test_updates_each_ru_battery_using_its_current_status -v`

Expected: FAIL with `AttributeError` because `Environment.update_batteries` does not exist.

- [ ] **Step 3: Implement the minimal battery operation**

Add this public method to `Environment`:

```python
def update_batteries(self) -> None:
    for ru in self._rus:
        ru.update_battery()
```

- [ ] **Step 4: Run the battery test to verify it passes**

Run: `uv run pytest tests/environment/test_environment.py::test_updates_each_ru_battery_using_its_current_status -v`

Expected: PASS; active and sleeping RUs consume their respective configured amounts.

- [ ] **Step 5: Write the failing connectivity-rebuild test**

Append this test to `tests/environment/test_connectivity.py`:

```python
def test_rebuilds_connectivity_graph_with_the_next_seeded_random_values() -> None:
    environment = make_environment(random_seed=7)
    initial_weights = edge_weights_by_ids(environment)

    environment.update_connectivity_graph()

    assert edge_weights_by_ids(environment) != initial_weights
```

- [ ] **Step 6: Run the connectivity test to verify it fails**

Run: `uv run pytest tests/environment/test_connectivity.py::test_rebuilds_connectivity_graph_with_the_next_seeded_random_values -v`

Expected: FAIL with `AttributeError` because `Environment.update_connectivity_graph` does not exist.

- [ ] **Step 7: Implement the minimal connectivity operation**

Add this public method to `Environment`:

```python
def update_connectivity_graph(self) -> None:
    self._connectivity_graph = self._create_connectivity_graph()
```

- [ ] **Step 8: Run the focused environment tests to verify they pass**

Run: `uv run pytest tests/environment/test_environment.py tests/environment/test_connectivity.py -v`

Expected: PASS; the new methods preserve all existing environment behavior.

- [ ] **Step 9: Commit the environment operations**

```bash
git add src/simulator/environment/environment.py tests/environment
git commit -m "feat: add environment step updates"
```

### Task 4: Implement Simulation Construction and Configured Runs

**Files:**
- Modify: `src/simulator/simulation.py`
- Modify: `tests/test_simulation.py`

**Interfaces:**
- Consumes: `ApplicationConfig`, `Environment`, `build_controller`, and an iterable of `MetricCollector` instances.
- Produces: `Simulation(config: ApplicationConfig, metric_collectors: Iterable[MetricCollector] = ())`.
- Produces: read-only `timestamp: int` and `environment: Environment` properties.
- Produces: public `simulate() -> None`, which calls private `_step() -> None` exactly `config.simulation.steps` times.
- Produces: private `_step() -> None`, ordered as environment battery update, controller status update with the new timestamp, graph rebuild, then each collector's `collect(environment)`.

- [ ] **Step 1: Write the failing construction test and test helpers**

Replace `tests/test_simulation.py` with the following initial test support and construction test:

```python
from simulator.configuration import (
    ApplicationConfig,
    ControllerConfig,
    ControllerKind,
    LoggingConfig,
    SimulationConfig,
    TimestampConfig,
)
from simulator.domain import RUStatus
from simulator.metrics import MetricCollector
from simulator.simulation import Simulation
from simulator.environment import EnvironmentConfig, MapConfig, RUConfig


def make_application_config(steps: int = 1) -> ApplicationConfig:
    return ApplicationConfig(
        environment=EnvironmentConfig(
            map=MapConfig(width=2, height=1),
            ru=RUConfig(
                count=1,
                initial_battery=10.0,
                initial_status=RUStatus.SLEEP,
                active_consumption=3.0,
                sleep_consumption=1.0,
                coverage_radius=2.0,
            ),
            user_count=1,
            random_seed=7,
        ),
        controller=ControllerConfig(ControllerKind.ALWAYS_ACTIVE),
        logging=LoggingConfig(
            logger_name="simulator",
            level=20,
            destination="stdout",
            format="json",
            include_logger_name=True,
            include_log_level=True,
            timestamp=TimestampConfig(key="logged_at", format="iso", utc=True),
            cache_loggers_on_first_use=True,
            propagate=False,
        ),
        simulation=SimulationConfig(steps=steps),
    )


def test_starts_at_timestamp_zero_with_configured_environment() -> None:
    simulation = Simulation(make_application_config())

    assert simulation.timestamp == 0
    assert len(simulation.environment.get_rus()) == 1
    assert len(simulation.environment.get_users()) == 1
```

- [ ] **Step 2: Run the construction test to verify it fails**

Run: `uv run pytest tests/test_simulation.py::test_starts_at_timestamp_zero_with_configured_environment -v`

Expected: FAIL during collection because `Simulation` is not defined.

- [ ] **Step 3: Implement the minimal construction API**

```python
from collections.abc import Iterable

from simulator.configuration import ApplicationConfig, build_controller
from simulator.environment import Environment
from simulator.metrics import MetricCollector


class Simulation:
    def __init__(
        self,
        config: ApplicationConfig,
        metric_collectors: Iterable[MetricCollector] = (),
    ) -> None:
        self._config = config
        self._timestamp = 0
        self._environment = Environment(config.environment)
        self._controller = build_controller(config.controller)
        self._metric_collectors = list(metric_collectors)

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    def environment(self) -> Environment:
        return self._environment
```

- [ ] **Step 4: Run the construction test to verify it passes**

Run: `uv run pytest tests/test_simulation.py::test_starts_at_timestamp_zero_with_configured_environment -v`

Expected: PASS; the simulation exposes timestamp `0` and the configured entities.

- [ ] **Step 5: Write the failing ordered-step test**

Append this collector and test to `tests/test_simulation.py`:

```python
class RecordingCollector(MetricCollector):
    def __init__(self) -> None:
        self.observations: list[tuple[float, RUStatus, float]] = []

    def collect(self, environment: Environment) -> None:
        ru = environment.get_rus()[0]
        user = environment.get_users()[0]
        self.observations.append(
            (ru.get_battery(), ru.get_status(), environment.get_connection_weight(user, ru))
        )


def test_simulate_updates_state_before_collecting_metrics() -> None:
    collector = RecordingCollector()
    simulation = Simulation(make_application_config(), [collector])
    ru = simulation.environment.get_rus()[0]
    user = simulation.environment.get_users()[0]
    initial_weight = simulation.environment.get_connection_weight(user, ru)

    simulation.simulate()

    assert simulation.timestamp == 1
    assert ru.get_battery() == 9.0
    assert ru.get_status() is RUStatus.ACTIVE
    assert collector.observations == [
        (9.0, RUStatus.ACTIVE, simulation.environment.get_connection_weight(user, ru))
    ]
    assert collector.observations[0][2] != initial_weight
```

Add these imports needed by the collector:

```python
from simulator.environment import Environment
```

- [ ] **Step 6: Run the ordered-step test to verify it fails**

Run: `uv run pytest tests/test_simulation.py::test_simulate_updates_state_before_collecting_metrics -v`

Expected: FAIL with `AttributeError` because `Simulation.simulate` does not exist.


- [ ] **Step 7: Implement the public run loop and private ordered step**

Add these methods to `Simulation`:

```python
def simulate(self) -> None:
    for _ in range(self._config.simulation.steps):
        self._step()

def _step(self) -> None:
    self._timestamp += 1
    self._environment.update_batteries()
    self._controller.update(self._environment.get_rus(), self._timestamp)
    self._environment.update_connectivity_graph()
    for collector in self._metric_collectors:
        collector.collect(self._environment)
```

- [ ] **Step 8: Add and run the repeated-step regression test**

Append this test to `tests/test_simulation.py`:

```python
def test_simulate_uses_the_status_selected_by_the_previous_iteration() -> None:
    simulation = Simulation(make_application_config(steps=2))

    simulation.simulate()

    ru = simulation.environment.get_rus()[0]
    assert simulation.timestamp == 2
    assert ru.get_battery() == 6.0
    assert ru.get_status() is RUStatus.ACTIVE
```

Run: `uv run pytest tests/test_simulation.py -v`

Expected: PASS; `simulate()` performs two iterations: the first consumes sleep power and the second consumes active power.

- [ ] **Step 9: Commit simulation orchestration**

```bash
git add src/simulator/simulation.py tests/test_simulation.py
git commit -m "feat: orchestrate simulation steps"
```

### Task 5: Document the Implemented Lifecycle

**Files:**
- Modify: `README.md`

**Interfaces:**
- Documents: `Simulation(config, metric_collectors=())`, `timestamp`, `environment`, and `simulate()`.
- Documents: the future application composition root owns configuration loading, logging configuration, and collector creation.

- [ ] **Step 1: Update the capability summary**

Replace this sentence in the opening paragraph:

```text
Simulation orchestration and metric calculations remain scaffolded for later phases.
```

with:

```text
Simulation orchestration is implemented; concrete metric calculations remain for later phases.
```

- [ ] **Step 2: Add the Simulation section after RU Controllers**

```markdown
## Simulation

`Simulation` is the entry point for one already-loaded `ApplicationConfig`.
It creates the environment and configured RU controller, starts at timestamp
`0`, and accepts optional metric collector instances. Calling `simulate()` runs
the positive `simulation.steps` count from configuration. Each private step
increments the timestamp, depletes batteries using prior statuses, applies the
RU controller, rebuilds connectivity, and then calls each collector with the
completed environment.

```python
from simulator.configuration import load_config
from simulator.simulation import Simulation

config = load_config(Path("configs/default.yaml"))
simulation = Simulation(config)
simulation.simulate()
```

A future application entry point will load configuration, configure logging,
create concrete collectors, and pass them to `Simulation`.
```

- [ ] **Step 3: Verify the complete README code sample is internally consistent**

Ensure the existing `from pathlib import Path` import appears before the new
example, or add it inside the example so the snippet has all of its imports.

- [ ] **Step 4: Commit the documentation**

```bash
git add README.md
git commit -m "docs: describe simulation lifecycle"
```

### Task 6: Run Full Verification

**Files:**
- Verify: all changed files from Tasks 1-5.

**Interfaces:**
- Verifies: run configuration parsing, the public metric collector interface, environment step operations, configured simulation runs, and project quality gates.

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest`

Expected: PASS with every test collected and no failures.

- [ ] **Step 2: Run linting**

Run: `uv run ruff check .`

Expected: PASS with no diagnostics.

- [ ] **Step 3: Check formatting**

Run: `uv run ruff format --check .`

Expected: PASS with no files requiring formatting.

- [ ] **Step 4: Check the final diff**

Run: `git status --short && git diff main...HEAD && git diff --check main...HEAD`

Expected: only the planned simulation-orchestration changes; no whitespace errors.
