# Structured JSON Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure `structlog` once at application startup and migrate every existing simulator log event to structured INFO-level JSON.

**Architecture:** A focused `simulator.logging` module configures the `simulator` standard-library logger hierarchy as the output backend for `structlog`, with one stdout handler and a JSON processor chain. Controller modules obtain module-local `structlog` loggers and emit structured domain fields; importing the package has no configuration side effect.

**Tech Stack:** Python 3.12, structlog, standard-library `logging`/`json`, uv, pytest, Ruff

## Global Constraints

- All simulator logging uses `structlog`; no simulator module emits events through standard-library logger methods.
- The hard-coded minimum level is INFO.
- Accepted events are newline-delimited JSON on standard output with a UTC ISO `logged_at` timestamp, level, and logger name.
- The `logged_at` field must not overwrite a domain event's simulation `timestamp` field.
- Loggers are cached on first use because configuration is fixed after startup.
- Logging configuration, formatting, filtering, event emission, and event absence are intentionally not tested.
- Task 3 supersedes the logging-test steps from Tasks 1 and 2 while retaining their controller state coverage.
- `configure_logging() -> None` is called explicitly by the future application entry point and is not called on package import.
- Do not add environment variables, configuration objects, alternate renderers, log files, or foreign standard-library logging integration.
- Preserve the always-active controller's existing no-log behavior.
- Use uv for dependency changes and commit the updated `uv.lock`.
- Run pytest and Ruff verification before completion.

---

### Task 1: Add hard-coded structured logging configuration

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `src/simulator/logging.py`
- Create: `tests/test_logging.py`
- Include: `docs/superpowers/plans/2026-07-16-structured-logging.md`

**Interfaces:**

- Consumes: the `structlog` runtime package and the `simulator` logger hierarchy.
- Produces: `simulator.logging.configure_logging() -> None`, which writes INFO-and-higher simulator events as JSON to stdout.

- [ ] **Step 1: Add the runtime dependency through uv**

Run:

```bash
uv add structlog
```

Expected: `pyproject.toml` lists `structlog` under project dependencies and `uv.lock` contains the resolved package.

- [ ] **Step 2: Write failing configuration tests**

Create `tests/test_logging.py`:

```python
import json
from datetime import datetime

import structlog

from simulator.logging import configure_logging


def test_emits_info_event_as_json(capsys) -> None:
    configure_logging()
    logger = structlog.get_logger("simulator.test")

    logger.info("simulation_started", run_id=7)

    event = json.loads(capsys.readouterr().out)
    assert event["event"] == "simulation_started"
    assert event["run_id"] == 7
    assert event["level"] == "info"
    assert event["logger"] == "simulator.test"
    assert datetime.fromisoformat(event["logged_at"]).tzinfo is not None


def test_preserves_structured_timestamp_field(capsys) -> None:
    configure_logging()
    logger = structlog.get_logger("simulator.test")

    logger.info("simulation_started", timestamp=7)

    event = json.loads(capsys.readouterr().out)
    assert event["timestamp"] == 7
    assert datetime.fromisoformat(event["logged_at"]).tzinfo is not None


def test_filters_debug_event(capsys) -> None:
    configure_logging()
    logger = structlog.get_logger("simulator.test")

    logger.debug("simulation_details")

    assert capsys.readouterr().out == ""
```

- [ ] **Step 3: Run the tests and verify RED**

Run:

```bash
uv run pytest tests/test_logging.py -v
```

Expected: test collection fails with `ModuleNotFoundError: No module named 'simulator.logging'`.

- [ ] **Step 4: Add the minimal logging configuration**

Create `src/simulator/logging.py`:

```python
import logging
import sys

import structlog

_LOGGER_NAME = "simulator"


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))

    simulator_logger = logging.getLogger(_LOGGER_NAME)
    for existing_handler in simulator_logger.handlers:
        existing_handler.close()
    simulator_logger.handlers = [handler]
    simulator_logger.setLevel(logging.INFO)
    simulator_logger.propagate = False

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="logged_at"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
```

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run:

```bash
uv run pytest tests/test_logging.py -v
```

Expected: both logging configuration tests pass.

- [ ] **Step 6: Commit the configuration slice**

Run:

```bash
git add pyproject.toml uv.lock src/simulator/logging.py tests/test_logging.py docs/superpowers/plans/2026-07-16-structured-logging.md
git diff --cached --check
git commit -m "feat: configure structured JSON logging"
```

Expected: the dependency, configuration, tests, and implementation plan are committed together.

### Task 2: Migrate controller logs to structured events

**Files:**

- Modify: `src/simulator/controllers/utils.py`
- Modify: `src/simulator/controllers/staggered_active.py`
- Modify: `src/simulator/controllers/threshold_staggered_active.py`
- Modify: `tests/controllers/test_always_active.py`
- Modify: `tests/controllers/test_staggered_active.py`
- Modify: `tests/controllers/test_threshold_staggered_active.py`
- Modify: `README.md`

**Interfaces:**

- Consumes: module-local loggers returned by `structlog.get_logger(__name__)` and `_set_selected_status(...)`'s existing optional logger boundary.
- Produces: the `ru_activation_failed` INFO event with `controller`, `ru_id`, `timestamp`, `battery`, and `required_battery` fields.

- [ ] **Step 1: Replace message-oriented controller assertions with failing structured-event assertions**

In each controller test module, remove `import logging` and add:

```python
from structlog.testing import capture_logs
```

Replace `test_selected_underpowered_ru_sleeps_and_logs_info` in `tests/controllers/test_staggered_active.py` with:

```python
def test_selected_underpowered_ru_sleeps_and_logs_info() -> None:
    ru = make_ru(2, battery=1.0)

    with capture_logs() as logs:
        StaggeredActiveController().update([ru], timestamp=7)

    assert ru.get_status() is RUStatus.SLEEP
    assert logs == [
        {
            "event": "ru_activation_failed",
            "controller": "StaggeredActiveController",
            "ru_id": 2,
            "timestamp": 7,
            "battery": 1.0,
            "required_battery": 2.0,
            "log_level": "info",
        }
    ]
```

Replace `test_non_selected_ru_sleeps_without_log` in that file with:

```python
def test_non_selected_ru_sleeps_without_log() -> None:
    ru = make_ru(1, battery=1.0)

    with capture_logs() as logs:
        StaggeredActiveController().update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP
    assert logs == []
```

Replace `test_underpowered_ru_logs_info_before_transition` in `tests/controllers/test_threshold_staggered_active.py` with:

```python
def test_underpowered_ru_logs_info_before_transition() -> None:
    ru = make_ru(1, battery=1.0, active_consumption=2.0)

    with capture_logs() as logs:
        ThresholdStaggeredActiveController(0.0).update([ru], timestamp=3)

    assert ru.get_status() is RUStatus.SLEEP
    assert logs == [
        {
            "event": "ru_activation_failed",
            "controller": "ThresholdStaggeredActiveController",
            "ru_id": 1,
            "timestamp": 3,
            "battery": 1.0,
            "required_battery": 2.0,
            "log_level": "info",
        }
    ]
```

Replace `test_selected_underpowered_ru_logs_info_after_transition` in that file with:

```python
def test_selected_underpowered_ru_logs_info_after_transition() -> None:
    ru = make_ru(2, battery=1.0, active_consumption=2.0)

    with capture_logs() as logs:
        ThresholdStaggeredActiveController(100.0).update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP
    assert len(logs) == 1
    assert logs[0]["event"] == "ru_activation_failed"
```

Replace `test_underpowered_ru_does_not_log` in `tests/controllers/test_always_active.py` with:

```python
def test_underpowered_ru_does_not_log() -> None:
    ru = make_ru(battery=1.0, status=RUStatus.ACTIVE)

    with capture_logs() as logs:
        AlwaysActiveController().update([ru], timestamp=4)

    assert logs == []
```

- [ ] **Step 2: Run the controller log tests and verify RED**

Run:

```bash
uv run pytest tests/controllers/test_always_active.py tests/controllers/test_staggered_active.py tests/controllers/test_threshold_staggered_active.py -v
```

Expected: structured logging assertions fail because the controllers still emit formatted standard-library messages that `capture_logs()` cannot capture.

- [ ] **Step 3: Migrate the controller loggers and event payload**

In `src/simulator/controllers/staggered_active.py` and `src/simulator/controllers/threshold_staggered_active.py`, replace `import logging` and the module logger with:

```python
import structlog

logger = structlog.get_logger(__name__)
```

Update `src/simulator/controllers/utils.py` to use this logger type and structured event:

```python
from structlog.stdlib import BoundLogger

from simulator.domain.ru import RU, RUStatus


def _validate_timestamp(timestamp: int) -> None:
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
        raise ValueError("timestamp must be a non-negative integer")


def _can_activate(ru: RU) -> bool:
    return ru.get_battery() >= ru.active_consumption


def _is_selected_for_timestamp(ru: RU, timestamp: int) -> bool:
    selected_id_parity = (timestamp // 10) % 2
    return ru.id % 2 == selected_id_parity


def _set_selected_status(
    ru: RU,
    timestamp: int,
    controller_name: str,
    logger: BoundLogger | None = None,
) -> None:
    if _can_activate(ru):
        ru.set_status(RUStatus.ACTIVE)
        return

    ru.set_status(RUStatus.SLEEP)
    if logger is not None:
        logger.info(
            "ru_activation_failed",
            controller=controller_name,
            ru_id=ru.id,
            timestamp=timestamp,
            battery=ru.get_battery(),
            required_battery=ru.active_consumption,
        )
```

- [ ] **Step 4: Run the controller tests and verify GREEN**

Run:

```bash
uv run pytest tests/controllers/test_always_active.py tests/controllers/test_staggered_active.py tests/controllers/test_threshold_staggered_active.py -v
```

Expected: all controller tests pass with structured logging assertions.

- [ ] **Step 5: Document startup configuration and structured event usage**

Add this section to `README.md` before `## Setup`:

````markdown
## Logging

The simulator uses `structlog` and emits INFO-and-higher events as one JSON
object per line on standard output. Configure logging once in the future
application entry point before running the simulation:

```python
from simulator.logging import configure_logging

configure_logging()
```

Modules obtain their own named logger and attach domain data as fields:

```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("simulation_started", timestamp=0)
```
````

- [ ] **Step 6: Run complete verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Expected: the full test suite passes, Ruff reports no lint or formatting failures, and Git reports no whitespace errors.

- [ ] **Step 7: Commit the migration**

Run:

```bash
git add src/simulator/logging.py src/simulator/controllers/utils.py src/simulator/controllers/staggered_active.py src/simulator/controllers/threshold_staggered_active.py tests/test_logging.py tests/controllers/test_always_active.py tests/controllers/test_staggered_active.py tests/controllers/test_threshold_staggered_active.py docs/superpowers/specs/2026-07-16-structured-logging-design.md docs/superpowers/plans/2026-07-16-structured-logging.md README.md
git diff --cached --check
git commit -m "refactor: migrate controller logs to structlog"
```

Expected: the controller migration, updated tests, and README are committed with no unrelated files.

### Task 3: Cache loggers and remove logging tests

**Files:**

- Modify: `src/simulator/logging.py`
- Delete: `tests/test_logging.py`
- Modify: `tests/controllers/test_always_active.py`
- Modify: `tests/controllers/test_staggered_active.py`
- Modify: `tests/controllers/test_threshold_staggered_active.py`
- Modify: `docs/superpowers/plans/2026-07-16-structured-logging.md`

**Interfaces:**

- Consumes: the existing hard-coded `configure_logging() -> None` function and controller state tests.
- Produces: cached logger assembly after first use and a test suite that covers controller state without asserting logging behavior.

- [ ] **Step 1: Enable logger caching**

In `src/simulator/logging.py`, change the final `structlog.configure()` argument to:

```python
        cache_logger_on_first_use=True,
```

- [ ] **Step 2: Delete the dedicated logging test module**

Delete `tests/test_logging.py` in full. No replacement logging configuration test is added because logging infrastructure is intentionally outside the test contract.

- [ ] **Step 3: Convert the always-active logging test to state-only coverage**

Remove this import from `tests/controllers/test_always_active.py`:

```python
from structlog.testing import capture_logs
```

Replace `test_underpowered_ru_does_not_log` with:

```python
def test_underpowered_ru_remains_asleep() -> None:
    ru = make_ru(battery=1.0, status=RUStatus.ACTIVE)

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.SLEEP
```

- [ ] **Step 4: Convert staggered logging tests to state-only coverage**

Remove this import from `tests/controllers/test_staggered_active.py`:

```python
from structlog.testing import capture_logs
```

Replace the two logging-oriented tests with:

```python
def test_selected_underpowered_ru_sleeps() -> None:
    ru = make_ru(2, battery=1.0)

    StaggeredActiveController().update([ru], timestamp=7)

    assert ru.get_status() is RUStatus.SLEEP


def test_non_selected_ru_sleeps() -> None:
    ru = make_ru(1, battery=1.0)

    StaggeredActiveController().update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP
```

- [ ] **Step 5: Convert threshold logging tests to state-only coverage**

Remove this import from `tests/controllers/test_threshold_staggered_active.py`:

```python
from structlog.testing import capture_logs
```

Replace the two logging-oriented tests with:

```python
def test_underpowered_ru_sleeps_before_transition() -> None:
    ru = make_ru(1, battery=1.0, active_consumption=2.0)

    ThresholdStaggeredActiveController(0.0).update([ru], timestamp=3)

    assert ru.get_status() is RUStatus.SLEEP


def test_selected_underpowered_ru_sleeps_after_transition() -> None:
    ru = make_ru(2, battery=1.0, active_consumption=2.0)

    ThresholdStaggeredActiveController(100.0).update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP
```

- [ ] **Step 6: Run complete verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
rg -n "capture_logs|test_logging|does_not_log|logs_info" tests
```

Expected: the test suite and Ruff checks pass, Git reports no whitespace errors, and `rg` exits with status 1 because no logging-test references remain.

- [ ] **Step 7: Commit the cache and test-policy change**

Run:

```bash
git add src/simulator/logging.py tests/controllers/test_always_active.py tests/controllers/test_staggered_active.py tests/controllers/test_threshold_staggered_active.py docs/superpowers/plans/2026-07-16-structured-logging.md
git add -u tests/test_logging.py
git diff --cached --check
git commit -m "test: remove logging behavior coverage"
```

Expected: logger caching, state-only controller tests, deletion of the dedicated logging tests, and the revised implementation plan are committed together.
