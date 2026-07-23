# Logging Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single `simulator.logging` module with an internal logging package while preserving the public `configure_logging` import.

**Architecture:** The new `simulator.logging` package presents `configure_logging` from its `__init__.py` façade. The existing structlog and standard-library configuration code moves unchanged into `simulator.logging.configuration`, keeping configuration ownership separate from future logging helpers.

**Tech Stack:** Python 3.12, structlog, pytest, Ruff, uv

## Global Constraints

- Preserve `from simulator.logging import configure_logging` as the public API.
- Do not add a logger wrapper or change structured logging behavior.
- Keep configuration explicit; importing the package must not configure logging.
- Add a regression test for the public package import.

---

### Task 1: Package the logging configuration

**Files:**
- Delete: `src/simulator/logging.py`
- Create: `src/simulator/logging/__init__.py`
- Create: `src/simulator/logging/configuration.py`
- Create: `tests/test_logging.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: the existing `configure_logging() -> None` implementation in `src/simulator/logging.py`.
- Produces: `simulator.logging.configure_logging() -> None`, re-exported from the package façade.

- [ ] **Step 1: Write the failing package façade test**

```python
import simulator.logging



def test_logging_is_a_package_that_exposes_configure_logging() -> None:
    assert hasattr(simulator.logging, "__path__")
    assert callable(simulator.logging.configure_logging)
```

- [ ] **Step 2: Run the test to verify it fails against the module**

Run: `uv run pytest tests/test_logging.py::test_logging_is_a_package_that_exposes_configure_logging -v`

Expected: FAIL because `simulator.logging` is currently a module and has no `__path__` package attribute.

- [ ] **Step 3: Create the minimal package façade and move the configuration code**

```python
# src/simulator/logging/__init__.py
from simulator.logging.configuration import configure_logging

__all__ = ["configure_logging"]
```

Move the existing `configure_logging() -> None` implementation unchanged to `src/simulator/logging/configuration.py`, then delete `src/simulator/logging.py`.

- [ ] **Step 4: Document the stable package-level import**

Keep the README example at `from simulator.logging import configure_logging` and state that it is the logging package's public configuration entry point.

- [ ] **Step 5: Run focused verification**

Run: `uv run pytest tests/test_logging.py -v`

Expected: PASS

- [ ] **Step 6: Run the complete quality suite**

Run: `uv run pytest && uv run ruff check . && uv run ruff format --check .`

Expected: all tests pass, Ruff reports no lint violations, and formatting needs no changes.

- [ ] **Step 7: Commit**

```bash
git add README.md src/simulator/logging tests/test_logging.py docs/superpowers/plans/2026-07-23-logging-package.md
git rm src/simulator/logging.py
git commit -m "refactor: package logging configuration"
```
