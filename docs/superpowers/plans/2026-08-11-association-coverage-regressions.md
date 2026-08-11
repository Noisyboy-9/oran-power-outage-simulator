# Association Coverage Regressions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic regression coverage for user-order capacity contention and uniform RU capacity propagation.

**Architecture:** This is test-only work. The environment already sorts users by ID while rebuilding associations and already passes `RUConfig.user_capacity` into every `RU`; tests will assert those externally observable outcomes without changing production code.

**Tech Stack:** Python 3.12, pytest, Ruff, uv.

## Global Constraints

- Modify only `tests/environment/test_environment.py`; do not change production code, configuration, APIs, or timing.
- Reuse the existing `Environment`, `make_config()`, and `rebuild_associations()` test helpers.
- Keep tests deterministic with controlled weighted edges.
- Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `git diff --check` before completion.

---

### Task 1: Add Association Ordering and Capacity-Propagation Regressions

**Files:**
- Modify: `tests/environment/test_environment.py`

**Interfaces:**
- Consumes: `Environment._update_associations(minimum_service_link_weight: float)` through existing `rebuild_associations()`, `Environment.get_associated_ru(user: User) -> RU | None`, and `RU.user_capacity: int`.
- Produces: regression tests only; no production interface changes.

- [ ] **Step 1: Add deterministic lower-user-ID capacity contention coverage**

  Add this test near the existing capacity tests. It deliberately reverses the
  internal storage order before rebuilding, then asserts the documented
  ascending-ID processing outcome:

  ```python
  def test_lower_user_id_wins_capacity_contention_despite_reversed_storage() -> None:
      environment = Environment(
          make_config(ru_count=1, user_count=2, user_capacity=1),
          RecordingController(),
          0.0,
      )
      ru = environment.get_rus()[0]
      lower_id_user, higher_id_user = environment.get_users()
      environment._users.reverse()

      rebuild_associations(
          environment,
          [(ru, lower_id_user, 0.9), (ru, higher_id_user, 0.9)],
          0.0,
      )

      assert environment.get_associated_ru(lower_id_user) is ru
      assert environment.get_associated_ru(higher_id_user) is None
  ```

- [ ] **Step 2: Add uniform RU capacity-propagation coverage**

  In `test_creates_uniform_rus_and_sequential_entity_ids`, set
  `user_capacity=2` in `make_config()` and add this assertion inside the
  existing loop:

  ```python
  assert ru.user_capacity == 2
  ```

- [ ] **Step 3: Run the focused environment test suite**

  Run:

  ```bash
  uv run pytest tests/environment/test_environment.py -v
  ```

  Expected: PASS. These are characterization regressions for behavior already
  implemented in `Environment`; no production change is expected or required.

- [ ] **Step 4: Run quality checks and commit**

  ```bash
  uv run ruff check .
  uv run ruff format --check .
  git diff --check
  git add tests/environment/test_environment.py
  git commit -m "test: cover association ordering and capacity propagation"
  ```

### Task 2: Run Repository-Wide Verification

**Files:**
- Verify only: repository-wide source and tests.

**Interfaces:**
- Confirms: the added regressions preserve the existing association and configuration behavior.

- [ ] **Step 1: Run the complete verification set**

  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  git diff --check
  ```

  Expected: all commands exit `0`.

- [ ] **Step 2: Inspect final branch state**

  ```bash
  git status --short
  git diff --check HEAD
  ```

  Expected: no uncommitted changes and no whitespace errors.

## Plan Self-Review

- **Spec coverage:** Task 1 implements both newly documented regression requirements; Task 2 validates the complete repository.
- **Placeholder scan:** All test setup, literal edges, assertions, commands, and commit scope are explicit.
- **Type consistency:** The plan uses the existing `User -> RU | None` lookup and the public `RU.user_capacity` attribute without introducing any interface.
