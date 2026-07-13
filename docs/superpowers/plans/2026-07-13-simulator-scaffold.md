# Simulator Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a minimal uv-managed Python 3.12 project structure for the custom simulator without implementing simulation behavior.

**Architecture:** Use a `src` package layout. Keep domain models, RU control policies, and metric collection in focused subpackages; keep environment state and top-level orchestration directly under the main package.

**Tech Stack:** Python 3.12, uv, hatchling, pytest, Ruff

## Global Constraints

- The outer project directory and import package are both named `simulator`.
- Python 3.12 is the minimum and selected development version.
- Python modules contain no simulation implementation in this phase.
- The scaffold remains small and introduces no CLI, persistence, visualization, or runtime configuration.

---

### Task 1: Create and verify the simulator project scaffold

**Files:**

- Create: `simulator/.gitignore`
- Create: `simulator/.python-version`
- Create: `simulator/README.md`
- Create: `simulator/pyproject.toml`
- Create: `simulator/src/simulator/__init__.py`
- Create: `simulator/src/simulator/domain/__init__.py`
- Create: `simulator/src/simulator/domain/point.py`
- Create: `simulator/src/simulator/domain/ru.py`
- Create: `simulator/src/simulator/domain/user.py`
- Create: `simulator/src/simulator/controllers/__init__.py`
- Create: `simulator/src/simulator/controllers/base.py`
- Create: `simulator/src/simulator/controllers/always_active.py`
- Create: `simulator/src/simulator/controllers/staggered_active.py`
- Create: `simulator/src/simulator/controllers/threshold_staggered_active.py`
- Create: `simulator/src/simulator/metrics/__init__.py`
- Create: `simulator/src/simulator/metrics/base.py`
- Create: `simulator/src/simulator/environment.py`
- Create: `simulator/src/simulator/simulation_controller.py`
- Create: `simulator/tests/domain/.gitkeep`
- Create: `simulator/tests/controllers/.gitkeep`
- Create: `simulator/tests/metrics/.gitkeep`
- Create: `simulator/tests/test_environment.py`
- Create: `simulator/tests/test_simulation_controller.py`
- Generate: `simulator/uv.lock`

**Interfaces:**

- Consumes: Python 3.12 and uv installed on the development machine.
- Produces: Importable package `simulator`; empty module locations for every approved responsibility; reproducible development dependencies through `uv.lock`.

- [x] **Step 1: Create project metadata**

Create `.python-version` containing `3.12`. Create `pyproject.toml` with standard `[build-system]` and `[project]` metadata, no runtime dependencies, a `dev` dependency group containing pytest and Ruff, pytest discovery rooted at `tests`, and Ruff targeting Python 3.12. Create `.gitignore` entries for virtual environments, Python caches, test/tool caches, coverage output, and Python build artifacts.

- [x] **Step 2: Create contributor documentation**

Create `README.md` documenting the project purpose, uv setup commands, the package structure, and the fact that simulation behavior is intentionally deferred.

- [x] **Step 3: Create package and test placeholders**

Create every package, module, test file, and `.gitkeep` file listed above. Keep all Python files empty so the scaffold establishes boundaries without prematurely defining interfaces.

- [x] **Step 4: Resolve the environment and lock dependencies**

Run: `cd simulator && uv sync --dev`

Expected: exit code 0, `.venv` created, the project installed as editable, and `uv.lock` generated.

- [x] **Step 5: Verify the package and tools**

Run: `cd simulator && uv run python -c "import simulator"`

Expected: exit code 0 with no output.

Run: `cd simulator && uv run pytest --version`

Expected: exit code 0 and a pytest version line.

Run: `cd simulator && uv run ruff check .`

Expected: exit code 0 with `All checks passed!`.

Run: `cd simulator && uv run ruff format --check .`

Expected: exit code 0 and all Python files already formatted.

- [x] **Step 6: Confirm the scaffold matches the approved tree**

Run: `cd simulator && find . -path './.venv' -prune -o -path './.ruff_cache' -prune -o -print | sort`

Expected: the approved metadata, documentation, `src/simulator`, mirrored test placeholders, and `uv.lock` are present; no implementation modules are missing.

- [x] **Step 7: Commit (skipped: workspace root is not a Git repository)**

If the project is later placed under Git version control, stage the `simulator` directory and commit with `chore: scaffold simulator project`. This step is skipped now because the workspace root is not a Git repository.
