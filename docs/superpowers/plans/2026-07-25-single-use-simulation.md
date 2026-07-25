# Single-Use Simulation Metric Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the repeated-call guard for the initial metric observation from `Simulation`.

**Architecture:** A simulation is single-use, so the initial collection helper always sends the `t=0` state to every collector. The timestamp and collection ordering remain unchanged. The test suite will describe one execution only and verify the obsolete state is absent.

**Tech Stack:** Python 3, pytest, uv.

## Global Constraints

- Keep `Environment` and metric service APIs unchanged.
- Preserve the initial `t=0` collection and its explanatory comment.
- `Simulation.simulate()` is a single-use operation; repeated invocation is outside its supported contract.

---

### Task 1: Remove the initial-collection guard

**Files:**
- Modify: `src/simulator/simulation.py:17-37`
- Modify: `tests/test_simulation.py:140-184`

**Interfaces:**
- Consumes: `MetricCollector.collect(environment: Environment, timestamp: int) -> None`.
- Produces: `Simulation.simulate() -> None`, which collects at timestamp `0` before its step loop and has no `_initial_metrics_collected` instance state.

- [ ] **Step 1: Write the failing lifecycle-state test**

Add this assertion to `test_starts_at_timestamp_zero_with_configured_environment` in `tests/test_simulation.py`:

```python
    assert not hasattr(simulation, "_initial_metrics_collected")
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/test_simulation.py::test_starts_at_timestamp_zero_with_configured_environment -v`

Expected: FAIL because `Simulation.__init__` still creates `_initial_metrics_collected`.

- [ ] **Step 3: Remove the guard and unsupported repeat-run assertions**

In `src/simulator/simulation.py`, delete:

```python
        self._initial_metrics_collected = False
```

and delete this branch and assignment from `_collect_initial_metrics`:

```python
        if self._initial_metrics_collected:
            return
        # ... existing collection loop remains here
        self._initial_metrics_collected = True
```

Keep the existing comment and collector loop intact. In
`tests/test_simulation.py`, retain the assertions for the timestamps `[0, 1,
2]` and the first run's states, then delete the second `simulation.simulate()`
call and its assertions from
`test_simulate_collects_initial_state_once_and_each_updated_state`.

- [ ] **Step 4: Run the focused simulation tests**

Run: `uv run pytest tests/test_simulation.py -v`

Expected: PASS; the lifecycle test still shows collection at `t=0` before
`environment.update(1)`, and the state test still records `[0, 1, 2]` for a
two-step simulation.

- [ ] **Step 5: Run the full verification suite**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Expected: every command exits successfully.

- [ ] **Step 6: Commit the implementation**

```bash
git add src/simulator/simulation.py tests/test_simulation.py
git commit -m "refactor: remove initial metric collection guard"
```
