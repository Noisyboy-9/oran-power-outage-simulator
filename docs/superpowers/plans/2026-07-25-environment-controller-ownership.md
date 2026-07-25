# Environment Controller Ownership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Environment` own the RU controller and its complete state-update lifecycle, simplifying `Simulation`.

**Architecture:** `Simulation` constructs the controller from `ApplicationConfig` and injects it into `Environment`. `Environment.update(timestamp)` updates batteries, applies the controller, adopts its returned RU list, and rebuilds connectivity. Simulation only advances time, delegates one environment update, and runs metric collectors.

**Tech Stack:** Python 3.12, pytest, Ruff, uv.

## Global Constraints

- Keep all existing environment getters public and unchanged.
- `Environment(config, controller)` owns the supplied controller.
- `Environment.update(timestamp)` order is battery update → controller update → `set_rus` → connectivity rebuild.
- `Simulation._step()` order is timestamp increment → `environment.update(timestamp)` → metric collection.
- Do not add dependencies, new configuration, CLI behavior, concrete metrics, or unrelated refactoring.

---

### Task 1: Move the Controller Lifecycle into Environment

**Files:**
- Modify: `src/simulator/environment/environment.py`
- Modify: `tests/environment/test_environment.py`

**Interfaces:**
- Produces: `Environment(config: EnvironmentConfig, controller: RUController)`.
- Produces: `Environment.update(timestamp: int) -> None`.

- [ ] **Step 1: Write the failing environment lifecycle test**

Use a recording controller that returns its `rus` argument. Construct an
environment with it, call `environment.update(1)`, and assert the controller
received the environment RUs and timestamp `1`; assert each RU battery and
status reflect the prescribed order.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/environment/test_environment.py -v`

Expected: FAIL because the environment constructor does not accept a
controller and `update` does not exist.

- [ ] **Step 3: Implement the environment ownership boundary**

Store the injected controller as `_controller`. Add:

```python
def update(self, timestamp: int) -> None:
    self.update_batteries()
    self.set_rus(self._controller.update(self.get_rus(), timestamp))
    self.update_connectivity_graph()
```

- [ ] **Step 4: Run focused environment checks and commit**

Run: `uv run pytest tests/environment -v && uv run ruff check . && uv run ruff format --check .`

Expected: PASS.

```bash
git add src/simulator/environment/environment.py tests/environment/test_environment.py
git commit -m "feat: let environment own RU controller"
```

### Task 2: Simplify Simulation Delegation

**Files:**
- Modify: `src/simulator/simulation.py`
- Modify: `tests/test_simulation.py`

**Interfaces:**
- Consumes: `Environment(config.environment, build_controller(config.controller))` and `environment.update(timestamp)`.
- Produces: a simulation with no `_controller` member and a delegated `_step()`.

- [ ] **Step 1: Update the failing orchestration test**

Modify the recording environment test double to expose `update(timestamp)`.
Assert the ordered events are:

```python
["environment.update:1", "collector.collect"]
```

- [ ] **Step 2: Run the simulation test to verify it fails**

Run: `uv run pytest tests/test_simulation.py -v`

Expected: FAIL because simulation currently calls environment battery,
controller, and graph operations separately.

- [ ] **Step 3: Implement the delegation**

Construct `Environment` with the built controller, remove `_controller`, and
replace the internal lifecycle calls with:

```python
self._environment.update(self._timestamp)
```

- [ ] **Step 4: Run the complete quality suite and commit**

Run: `uv run pytest && uv run ruff check . && uv run ruff format --check . && git diff --check`

Expected: PASS.

```bash
git add src/simulator/simulation.py tests/test_simulation.py
git commit -m "refactor: delegate simulation updates to environment"
```
