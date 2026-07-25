# Environment Update Simplification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify `Environment.update()` by inlining the RU-list handoff and making its component updates private.

**Architecture:** `Environment.update(timestamp)` remains the only public state-update operation. It calls private battery and connectivity helpers, and directly shallow-copies the list returned by its controller into `_rus`. The redundant public `set_rus()` method is removed.

**Tech Stack:** Python 3.12, pytest, Ruff, uv.

## Global Constraints

- Retain all environment getters unchanged.
- Remove `set_rus()` completely.
- `update(timestamp)` preserves battery → controller → shallow-copy `_rus` → connectivity order.
- Rename `update_batteries()` and `update_connectivity_graph()` to private helpers.
- Do not add dependencies or alter simulation, controller, metric, or configuration behavior.

---

### Task 1: Simplify Environment Update Internals

**Files:**
- Modify: `src/simulator/environment/environment.py`
- Modify: `tests/environment/test_environment.py`
- Modify: `tests/environment/test_connectivity.py`

**Interfaces:**
- Produces: public `Environment.update(timestamp: int) -> None` as the sole update API.
- Produces: private `_update_batteries() -> None` and `_update_connectivity_graph() -> None`.

- [ ] **Step 1: Update failing tests**

Remove the direct `set_rus()` and direct public helper tests. Extend the
`Environment.update()` recording-controller test to retain the returned list,
clear it after `update()`, and assert `environment.get_rus()` still contains
the original RU objects. Keep the existing observable connectivity assertions.

- [ ] **Step 2: Run focused tests to verify failure**

Run: `uv run pytest tests/environment -v`

Expected: FAIL because public helpers and `set_rus()` still exist or the new
isolation assertion is not met.

- [ ] **Step 3: Implement the minimal simplification**

```python
def update(self, timestamp: int) -> None:
    self._update_batteries()
    self._rus = self._controller.update(self.get_rus(), timestamp).copy()
    self._update_connectivity_graph()
```

Rename the existing public helper definitions to `_update_batteries` and
`_update_connectivity_graph`, then delete `set_rus`.

- [ ] **Step 4: Run full verification and commit**

Run: `uv run pytest && uv run ruff check . && uv run ruff format --check . && git diff --check`

Expected: PASS.

```bash
git add src/simulator/environment tests/environment
git commit -m "refactor: simplify environment updates"
```
