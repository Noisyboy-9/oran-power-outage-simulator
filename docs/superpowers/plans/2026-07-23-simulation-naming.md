# Simulation Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the simulation orchestration scaffold so it is distinct from
the RU-controller policy package.

**Architecture:** Rename the empty `simulation_controller.py` source and test
scaffolds to `simulation.py` and `test_simulation.py`. Preserve the
`simulator.controllers` package because it names the RU state-control policy
abstraction. Update current architecture references only; historical plans and
specifications remain unchanged.

**Tech Stack:** Python 3.12, pytest, Ruff, Git

## Global Constraints

- Do not add a `Simulation` class or define orchestration behavior.
- Do not rename `simulator.controllers` or `RUController`.
- Preserve historical documentation as an immutable record.
- Work directly on `main`, as explicitly authorized by the user.

---

### Task 1: Rename the scaffolds and current architecture references

**Files:**

- Rename: `src/simulator/simulation_controller.py` to
  `src/simulator/simulation.py`
- Rename: `tests/test_simulation_controller.py` to `tests/test_simulation.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Reference: `docs/superpowers/specs/2026-07-23-simulation-naming-design.md`

**Interfaces:**

- Consumes: the existing empty simulation source and test scaffold.
- Produces: `simulator.simulation` as the future simulation-orchestration
  module, without an implemented public interface.

- [x] **Step 1: Confirm the source and test scaffolds are empty**

Run:

```bash
wc -c src/simulator/simulation_controller.py tests/test_simulation_controller.py
```

Expected: both files have zero bytes, so no behavior or tests need migration.

- [x] **Step 2: Rename the empty scaffolds**

Run:

```bash
git mv src/simulator/simulation_controller.py src/simulator/simulation.py
git mv tests/test_simulation_controller.py tests/test_simulation.py
```

- [x] **Step 3: Update current architecture references**

Replace the `simulation_controller.py` path in `README.md` and `AGENTS.md`
with `simulation.py`. Keep their description as time-step and component
orchestration.

- [x] **Step 4: Verify source, tests, formatting, and whitespace**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Expected: tests and quality checks exit successfully; Git reports no whitespace
errors.

- [x] **Step 5: Review and commit the focused rename**

Run:

```bash
git status --short
git diff --cached --check
git commit -m "refactor: rename simulation orchestrator"
```

Expected: one commit contains only the scaffold rename and its supporting
documentation.
