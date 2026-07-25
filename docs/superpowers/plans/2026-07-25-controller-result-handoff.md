# Controller Result Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make RU controllers return their updated RU list and have `Simulation` give that result back to the environment through `set_rus()`.

**Architecture:** Controllers remain responsible only for status policy, but their `update()` method returns the same input list after applying policy. The environment trusts that controller boundary and stores a shallow copy of the returned list, preserving collection encapsulation while retaining the shared RU objects and their updated statuses. `Simulation._step()` coordinates the explicit handoff before rebuilding connectivity.

**Tech Stack:** Python 3.12, pytest, Ruff, uv.

## Global Constraints

- Target Python 3.12 or newer with public type hints.
- Controllers must return the input RU list with updated statuses; no replacement RU instances are created.
- `Environment.set_rus()` trusts controllers and does no validation; it stores `rus.copy()` to prevent callers from later changing the environment's list structure.
- The `RUController` and `Environment.set_rus()` docstrings must explain their trusted-handoff responsibilities.
- Preserve the existing step order: battery update, controller update, `set_rus`, graph rebuild, metric collection.
- Do not add dependencies, metrics, configuration, CLI, or application-startup behavior.

---

### Task 1: Return the Controller Result

**Files:**
- Modify: `src/simulator/controllers/base.py`
- Modify: `src/simulator/controllers/always_active.py`
- Modify: `src/simulator/controllers/staggered_active.py`
- Modify: `src/simulator/controllers/threshold_staggered_active.py`
- Modify: `tests/controllers/test_always_active.py`
- Modify: `tests/controllers/test_staggered_active.py`
- Modify: `tests/controllers/test_threshold_staggered_active.py`

**Interfaces:**
- Produces: `RUController.update(self, rus: list[RU], timestamp: int) -> list[RU]`.
- Produces: each concrete controller returns the same `rus` list after status updates, including an empty list.

- [ ] **Step 1: Write failing return-value tests**

Add one test to each concrete-controller test module, following this form:

```python
def test_returns_the_supplied_ru_list() -> None:
    rus = [make_ru()]

    result = AlwaysActiveController().update(rus, timestamp=0)

    assert result is rus
```

Use the module's existing controller and helper. Add an equivalent empty-list assertion where the module already tests an empty list.

- [ ] **Step 2: Run controller tests to verify they fail**

Run: `uv run pytest tests/controllers -v`

Expected: FAIL because current `update()` methods return `None`.

- [ ] **Step 3: Update the interface and controller implementations**

Change the abstract interface to:

```python
def update(self, rus: list[RU], timestamp: int) -> list[RU]:
    """Update statuses and return the trusted environment RU list.

    Controllers return the supplied RU instances after policy application;
    the environment trusts this handoff and adopts the returned list.
    """
```

After each concrete controller finishes its existing status logic, add:

```python
return rus
```

For early empty-list returns, return `rus` rather than bare `return`.

- [ ] **Step 4: Run controller tests and quality checks**

Run: `uv run pytest tests/controllers -v && uv run ruff check . && uv run ruff format --check .`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/simulator/controllers tests/controllers
git commit -m "feat: return updated RUs from controllers"
```

### Task 2: Store the Controller Result in the Environment

**Files:**
- Modify: `src/simulator/environment/environment.py`
- Modify: `tests/environment/test_environment.py`

**Interfaces:**
- Produces: `Environment.set_rus(self, rus: list[RU]) -> None`.
- Consumes: the trusted RU list returned by `RUController.update`.

- [ ] **Step 1: Write the failing environment test**

```python
def test_sets_rus_without_sharing_the_list_container() -> None:
    environment = Environment(make_config(ru_count=1, user_count=1))
    rus = environment.get_rus()

    environment.set_rus(rus)
    rus.clear()

    assert len(environment.get_rus()) == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/environment/test_environment.py::test_sets_rus_without_sharing_the_list_container -v`

Expected: FAIL with `AttributeError` because `set_rus` does not exist.

- [ ] **Step 3: Implement the trusted handoff method**

```python
def set_rus(self, rus: list[RU]) -> None:
    """Store RUs returned by a trusted controller.

    The list is copied so a caller cannot subsequently change the
    environment's collection structure through its original list reference.
    The contained RU objects remain shared, retaining their updated statuses.
    """
    self._rus = rus.copy()
```

- [ ] **Step 4: Run focused environment tests**

Run: `uv run pytest tests/environment -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/simulator/environment/environment.py tests/environment/test_environment.py
git commit -m "feat: store controller RU results"
```

### Task 3: Complete the Simulation Handoff

**Files:**
- Modify: `src/simulator/simulation.py`
- Modify: `tests/test_simulation.py`

**Interfaces:**
- Consumes: `controller.update(rus, timestamp) -> list[RU]` and `environment.set_rus(rus) -> None`.
- Produces: `_step()` that calls `set_rus` after policy selection and before graph rebuilding.

- [ ] **Step 1: Extend the existing orchestration recording test**

Use the existing test collaborators to assert this order:

```python
[
    "update_batteries",
    "controller.update:1",
    "set_rus",
    "update_connectivity_graph",
    "collector.collect",
]
```

Also assert that the exact list returned by the recording controller is the list passed to `set_rus`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_simulation.py -v`

Expected: FAIL because `_step()` currently ignores the controller return value.

- [ ] **Step 3: Implement the handoff**

Replace the controller call in `_step()` with:

```python
rus = self._controller.update(self._environment.get_rus(), self._timestamp)
self._environment.set_rus(rus)
```

- [ ] **Step 4: Run simulation tests and the complete suite**

Run: `uv run pytest tests/test_simulation.py -v && uv run pytest`

Expected: PASS.

- [ ] **Step 5: Run final quality checks and commit Task 3**

Run: `uv run ruff check . && uv run ruff format --check . && git diff --check`

Expected: PASS.

```bash
git add src/simulator/simulation.py tests/test_simulation.py
git commit -m "feat: hand controller RUs to environment"
```
