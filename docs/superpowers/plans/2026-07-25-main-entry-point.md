# Main Entry Point Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repository-root CLI that loads a required configuration file, configures logging, and runs one configured `Simulation`.

**Architecture:** `main.py` is the application composition root. It delegates CLI parsing to `argparse`, schema validation to `load_config`, logging setup to `configure_logging`, and all step execution to `Simulation.simulate()`. Until metric configuration and concrete collectors exist, it passes an explicit empty collector iterable to `Simulation` at the sole future collector-composition point.

**Tech Stack:** Python 3.12, standard-library `argparse`, pytest, Ruff, uv.

## Global Constraints

- The public command is `uv run python main.py --configs path/to/config.yaml`; `--configs` is required and has no default value.
- Use `argparse`; do not introduce a third-party CLI dependency or hand-written argument parser.
- Let `argparse` retain its normal `SystemExit(2)` behavior for missing or malformed arguments.
- After parsing succeeds, `main(argv: Sequence[str] | None = None) -> int` returns `0` after a completed run and `1` if `load_config` raises `ConfigurationError`.
- Report a configuration failure as `error: <message>` on standard error; do not configure logging or construct `Simulation` after that failure.
- `main.py` calls `Simulation(config, metric_collectors=()).simulate()` exactly once. It does not read `config.simulation.steps` or create a second step loop.
- Do not add metric configuration, concrete metric collectors, a console-script package entry point, signal handling, progress output, result persistence, or new dependencies.
- This entry-point implementation assumes separately delivered public APIs: `Simulation.simulate()`, `ApplicationConfig.simulation`, `load_config`, `ConfigurationError`, and `configure_logging`.
- Run project commands from the repository root with `uv`.

---

## File Structure

- `main.py`: parses the required path, composes the configured application, and returns the process status.
- `tests/test_main.py`: verifies externally visible CLI and composition behavior without executing the real 10,000-step default run.
- `README.md`: documents the required invocation and explains that `simulation.steps` determines run length.

### Task 1: Add the test-driven CLI composition root

**Files:**

- Create: `tests/test_main.py`
- Create: `tests/__init__.py`
- Create: `main.py`

**Interfaces:**

- Consumes: `argparse`, `Path`, `Sequence`, `load_config`, `ConfigurationError`, `configure_logging`, and `Simulation`.
- Produces: `main(argv: Sequence[str] | None = None) -> int` and executable module behavior through `if __name__ == "__main__": raise SystemExit(main())`.

- [ ] **Step 1: Write failing CLI and composition tests**

Create `tests/test_main.py`:

```python
from pathlib import Path
from types import SimpleNamespace

import pytest

import main
from simulator.configuration import ConfigurationError


def test_requires_configs_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    load_config_called = False

    def fake_load_config(path: Path) -> object:
        nonlocal load_config_called
        load_config_called = True
        return object()

    monkeypatch.setattr(main, "load_config", fake_load_config)

    with pytest.raises(SystemExit) as error:
        main.main([])

    assert error.value.code == 2
    assert load_config_called is False


def test_loads_config_configures_logging_and_runs_simulation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []
    logging_config = object()
    config = SimpleNamespace(logging=logging_config)

    def fake_load_config(path: Path) -> object:
        events.append(("load", path))
        return config

    def fake_configure_logging(received_config: object) -> None:
        events.append(("configure_logging", received_config))

    class FakeSimulation:
        def __init__(
            self, received_config: object, *, metric_collectors: object
        ) -> None:
            events.append(("construct", received_config, metric_collectors))

        def simulate(self) -> None:
            events.append("simulate")

    monkeypatch.setattr(main, "load_config", fake_load_config)
    monkeypatch.setattr(main, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(main, "Simulation", FakeSimulation)

    assert main.main(["--configs", "example.yaml"]) == 0
    assert events == [
        ("load", Path("example.yaml")),
        ("configure_logging", logging_config),
        ("construct", config, ()),
        "simulate",
    ]


def test_reports_configuration_error_without_starting_application(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configured_logging = False
    constructed_simulation = False

    def fake_load_config(path: Path) -> object:
        raise ConfigurationError("simulation.steps: must be a positive integer")

    def fake_configure_logging(received_config: object) -> None:
        nonlocal configured_logging
        configured_logging = True

    class FakeSimulation:
        def __init__(
            self, received_config: object, *, metric_collectors: object
        ) -> None:
            nonlocal constructed_simulation
            constructed_simulation = True

        def simulate(self) -> None:
            raise AssertionError("must not run")

    monkeypatch.setattr(main, "load_config", fake_load_config)
    monkeypatch.setattr(main, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(main, "Simulation", FakeSimulation)

    assert main.main(["--configs", "invalid.yaml"]) == 1
    assert capsys.readouterr().err == (
        "error: simulation.steps: must be a positive integer\\n"
    )
    assert configured_logging is False
    assert constructed_simulation is False
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
uv run pytest tests/test_main.py -v
```

Expected: FAIL during collection because the repository-root `main` module does not yet exist. In the entry-point-only branch, run this test after the separate simulation/configuration work is available.

Create an empty `tests/__init__.py` before the passing run. This package marker
keeps the repository root on pytest's import path under the project's required
`uv run pytest` invocation, allowing the test to import the intentionally
repository-root `main.py` without adding a pytest configuration override.

- [ ] **Step 3: Implement the smallest CLI composition root**

Create `main.py`:

```python
import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from simulator.configuration import ConfigurationError, load_config
from simulator.logging import configure_logging
from simulator.simulation import Simulation


def _parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a dependable-networking simulation."
    )
    parser.add_argument(
        "--configs",
        required=True,
        metavar="PATH",
        help="path to the simulation YAML configuration file",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parse_arguments(argv)
    try:
        config = load_config(Path(arguments.configs))
    except ConfigurationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    configure_logging(config.logging)
    simulation = Simulation(config, metric_collectors=())
    simulation.simulate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Use the exact `metric_collectors=()` keyword so the empty current composition point is explicit and ready for future configured collector instances.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
uv run pytest tests/test_main.py -v
```

Expected: PASS. The required argument produces `SystemExit(2)`, successful composition follows the required order, and configuration errors return `1` before logging or simulation construction.

- [ ] **Step 5: Commit the CLI behavior**

Run:

```bash
git add main.py tests/__init__.py tests/test_main.py
git commit -m "feat: add simulation entry point"
```

Expected: one focused commit containing only the root CLI and its tests.

### Task 2: Document the executable application boundary

**Files:**

- Modify: `README.md`

**Interfaces:**

- Consumes: the public command `uv run python main.py --configs PATH` and `simulation.steps` from the configuration schema.
- Produces: user-facing instructions that match the implemented entry point.

- [ ] **Step 1: Inspect the existing documentation before editing**

Run:

```bash
rg -n "Simulation|orchestration|Logging|Setup" README.md
```

Expected: the existing text does not yet document the executable command or the configured run length.

- [ ] **Step 2: Add the application invocation section**

Add a `## Running a Simulation` section after `## Logging`:

````markdown
## Running a Simulation

Run the application with an explicit YAML configuration path:

```bash
uv run python main.py --configs configs/default.yaml
```

The required configuration's `simulation.steps` value determines how many ordered simulation steps run. `main.py` loads configuration, configures logging, constructs configured metric collectors, and starts `Simulation`. `Simulation` owns the ordered step loop.
````

Keep the collector statement accurate for the current empty collector set: it describes the composition boundary and does not claim that concrete collectors already exist.

- [ ] **Step 3: Run complete verification**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Expected: all tests pass and both Ruff commands exit `0`.

- [ ] **Step 4: Review the final diff for scope and whitespace**

Run:

```bash
git diff --check HEAD
git status --short
git diff HEAD -- main.py tests/test_main.py README.md
```

Expected: only the entry point, its tests, README documentation, and the previously committed design/plan documents appear; no whitespace errors.

- [ ] **Step 5: Commit the documentation**

Run:

```bash
git add README.md
git commit -m "docs: describe simulation command"
```

Expected: one focused documentation commit.
