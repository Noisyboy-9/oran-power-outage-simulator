# Configuration Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load an explicit YAML file into immutable typed application configuration and use its logging and controller settings to construct existing components.

**Architecture:** `simulator.configuration` owns YAML parsing, models, and component factories. Existing environment configuration models remain environment-facing. A composition root retains `ApplicationConfig` and explicitly passes branches to the environment, logger, and controller factory.

**Tech Stack:** Python 3.12, frozen dataclasses, `enum.StrEnum`, PyYAML, stdlib `logging`, structlog, pytest, Ruff, uv.

## Global Constraints

- Add PyYAML only through `uv add pyyaml`; update `pyproject.toml` and `uv.lock`.
- `load_config(path: Path)` uses `yaml.safe_load`, never loads at import time, and stores no global configuration.
- Reject unknown YAML keys and identify invalid values with dotted YAML paths.
- Do not add a CLI, environment-variable overrides, inheritance, caching, secrets, metrics, or simulation semantics.
- Run focused tests after each task, then complete pytest, Ruff lint, format, and whitespace verification.

---

### Task 1: Add the dependency and typed configuration models

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `src/simulator/configuration/__init__.py`
- Create: `src/simulator/configuration/errors.py`
- Create: `src/simulator/configuration/models.py`
- Create: `tests/configuration/__init__.py`
- Create: `tests/configuration/test_models.py`

**Interfaces:**

- Consumes: `simulator.environment.EnvironmentConfig`.
- Produces: `ConfigurationError`, `ApplicationConfig`, `ControllerKind`, `ControllerConfig`, `TimestampConfig`, and `LoggingConfig`.

- [ ] **Step 1: Add PyYAML**

Run `uv add pyyaml`. Expect `pyproject.toml` to contain a PyYAML runtime dependency and `uv.lock` to change.

- [ ] **Step 2: Write failing model tests**

Create `tests/configuration/test_models.py` with the following cases:

```python
def test_threshold_controller_accepts_in_range_percentage() -> None:
    config = ControllerConfig(
        kind=ControllerKind.THRESHOLD_STAGGERED_ACTIVE,
        threshold_percentage=50.0,
    )
    assert config.threshold_percentage == 50.0


@pytest.mark.parametrize("threshold", [None, -0.1, 100.1, True, "50"])
def test_threshold_controller_rejects_invalid_percentage(threshold: object) -> None:
    with pytest.raises(ValueError, match="threshold_percentage"):
        ControllerConfig(ControllerKind.THRESHOLD_STAGGERED_ACTIVE, threshold)


@pytest.mark.parametrize(
    "kind", [ControllerKind.ALWAYS_ACTIVE, ControllerKind.STAGGERED_ACTIVE]
)
def test_non_threshold_controller_rejects_threshold(kind: ControllerKind) -> None:
    with pytest.raises(ValueError, match="threshold_percentage"):
        ControllerConfig(kind, 50.0)
```

Also test a frozen `ControllerConfig` rejects assignment with `FrozenInstanceError`.

- [ ] **Step 3: Verify the test is red**

Run `uv run pytest tests/configuration/test_models.py -v`. Expect an import failure because the package does not exist.

- [ ] **Step 4: Implement models and exports**

Create `errors.py`:

```python
class ConfigurationError(ValueError):
    """Raised when a configuration file cannot be loaded or validated."""
```

Create frozen models. `ControllerKind` is a `StrEnum` with values
`always_active`, `staggered_active`, and `threshold_staggered_active`.
`ControllerConfig.kind` is a `ControllerKind` and its optional
`threshold_percentage` must be an `int | float` other than `bool` in `[0, 100]`
only for the threshold kind; other kinds reject a non-`None` threshold.

`TimestampConfig` has `key`, `format`, and `utc`. `LoggingConfig` has
`logger_name`, integer `level`, `destination`, `format`, include-name and
include-level booleans, `timestamp`, cache behavior, and propagation.
`ApplicationConfig` has `environment: EnvironmentConfig`,
`controller: ControllerConfig`, and `logging: LoggingConfig`. Re-export the
models and error from `__init__.py`.

- [ ] **Step 5: Verify the test is green**

Run `uv run pytest tests/configuration/test_models.py -v`. Expect PASS.

- [ ] **Step 6: Commit the task**

Run `git add pyproject.toml uv.lock src/simulator/configuration tests/configuration`, then run `git commit -m "feat: add configuration models"`.

### Task 2: Parse and validate YAML into application configuration

**Files:**

- Create: `src/simulator/configuration/loader.py`
- Modify: `src/simulator/configuration/__init__.py`
- Create: `tests/configuration/test_loader.py`

**Interfaces:**

- Consumes: `Path`, PyYAML, `RUStatus`, existing environment models, and Task 1 models.
- Produces: `load_config(path: Path) -> ApplicationConfig`.

- [ ] **Step 1: Write failing loader tests**

Use a `write_config(tmp_path, contents) -> Path` helper and complete `VALID_YAML`.
Cover a successful load, type conversion, and errors:

```python
def test_loads_typed_configuration(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, VALID_YAML))
    assert config.environment.ru.initial_status is RUStatus.ACTIVE
    assert config.logging.level == logging.INFO
    assert config.controller.kind is ControllerKind.THRESHOLD_STAGGERED_ACTIVE


def test_rejects_unknown_nested_key(tmp_path: Path) -> None:
    path = write_config(
        tmp_path, VALID_YAML.replace("count: 5", "count: 5\n    cout: 6")
    )
    with pytest.raises(ConfigurationError, match="environment.ru.cout"):
        load_config(path)


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_config(tmp_path / "missing.yaml")
```

Add cases for malformed and empty YAML, list roots, missing keys, invalid RU
status, invalid logging-level name, unsupported logging values, `utc: false`,
environment validation errors with their path, and valid/invalid combinations
for all controller kinds.

- [ ] **Step 2: Verify the loader tests are red**

Run `uv run pytest tests/configuration/test_loader.py -v`. Expect failure because `load_config` is absent.

- [ ] **Step 3: Implement `load_config` and helpers**

Implement this public entry point:

```python
def load_config(path: Path) -> ApplicationConfig:
    raw_config = _load_mapping(path)
    _require_exact_keys(raw_config, {"environment", "controller", "logging"}, "")
    return ApplicationConfig(
        environment=_parse_environment(raw_config["environment"], "environment"),
        controller=_parse_controller(raw_config["controller"], "controller"),
        logging=_parse_logging(raw_config["logging"], "logging"),
    )
```

`_load_mapping` catches `OSError` and `yaml.YAMLError`, rejects `None` and
non-mapping roots, and raises `ConfigurationError`. Private helpers validate
mappings, exact key sets, strings, booleans, positive integers, numbers, and
`int | None`; booleans never count as numbers. Every helper accepts the current
dotted path and includes it in its error.

Parse environment settings into existing `MapConfig`, `RUConfig`, and
`EnvironmentConfig`, converting `initial_status` with `RUStatus`. Convert
environment and domain validation errors into `ConfigurationError` while
preserving their YAML path. Parse `kind` with `ControllerKind` and use
`ControllerConfig` for threshold validation. Convert an uppercase standard
logging level through `logging.getLevelNamesMapping()`. Permit only `stdout`,
`json`, `iso`, and `timestamp.utc: true`. Export `load_config` in
`__init__.py`.

Before constructing `RUConfig`, validate `initial_battery`,
`active_consumption`, and `sleep_consumption` as positive YAML numbers (never
booleans), reporting their individual `environment.ru.<field>` paths. This
makes the whole typed configuration valid when `load_config` returns rather
than delaying those invalid values until `Environment` constructs RUs.

- [ ] **Step 4: Verify the loader tests are green**

Run `uv run pytest tests/configuration/test_loader.py -v`. Expect PASS.

- [ ] **Step 5: Commit the task**

Run `git add src/simulator/configuration tests/configuration`, then run `git commit -m "feat: load YAML configuration"`.

### Task 3: Construct configured components

**Files:**

- Create: `src/simulator/configuration/factories.py`
- Modify: `src/simulator/configuration/__init__.py`
- Modify: `src/simulator/logging.py`
- Create: `tests/configuration/test_factories.py`
- Create: `tests/test_logging.py`

**Interfaces:**

- Consumes: `ControllerConfig`, existing controller types, and `LoggingConfig`.
- Produces: `build_controller(config: ControllerConfig) -> RUController` and `configure_logging(config: LoggingConfig) -> None`.

- [ ] **Step 1: Write failing factory and logging tests**

Test that `always_active` builds `AlwaysActiveController`, `staggered_active`
builds `StaggeredActiveController`, and threshold config builds
`ThresholdStaggeredActiveController` retaining its percentage. With a full
`LoggingConfig`, test that the named standard-library logger receives the
specified numeric level, propagation flag, and one `sys.stdout` handler. Do not
assert dynamic timestamp values.

- [ ] **Step 2: Verify the tests are red**

Run `uv run pytest tests/configuration/test_factories.py tests/test_logging.py -v`. Expect failure because neither interface exists.

- [ ] **Step 3: Implement the factory and update logging**

Implement `build_controller` with exactly these branches:

```python
if config.kind is ControllerKind.ALWAYS_ACTIVE:
    return AlwaysActiveController()
if config.kind is ControllerKind.STAGGERED_ACTIVE:
    return StaggeredActiveController()
if config.kind is ControllerKind.THRESHOLD_STAGGERED_ACTIVE:
    assert config.threshold_percentage is not None
    return ThresholdStaggeredActiveController(config.threshold_percentage)
raise ValueError(f"unsupported controller kind: {config.kind}")
```

Export the factory. Change `configure_logging` to accept `LoggingConfig` and
use all its fields for logger assembly: name, level, stdout target, processor
include flags, timestamp key/format/UTC, JSON renderer, cache setting, and
propagation. The loader's strict schema means no fallback behavior is required.

- [ ] **Step 4: Verify the tests are green**

Run `uv run pytest tests/configuration/test_factories.py tests/test_logging.py -v`. Expect PASS.

- [ ] **Step 5: Commit the task**

Run `git add src/simulator/configuration src/simulator/logging.py tests/configuration tests/test_logging.py`, then run `git commit -m "feat: wire configured components"`.

### Task 4: Make the default file loadable and document setup

**Files:**

- Modify: `configs/default.yaml`
- Modify: `README.md`
- Modify: `tests/configuration/test_loader.py`

**Interfaces:**

- Consumes: `load_config`, `build_controller`, and `configure_logging`.
- Produces: a loadable default configuration and documented explicit setup.

- [ ] **Step 1: Write the default-file regression test**

```python
def test_loads_tracked_default_configuration() -> None:
    config_path = Path(__file__).parents[2] / "configs" / "default.yaml"
    config = load_config(config_path)
    assert config.environment.map.width == 20
    assert config.controller.kind is ControllerKind.THRESHOLD_STAGGERED_ACTIVE
    assert config.logging.level == logging.INFO
```

- [ ] **Step 2: Verify the test is red**

Run `uv run pytest tests/configuration/test_loader.py::test_loads_tracked_default_configuration -v`. Expect failure because the file has `controllers`, not `controller`.

- [ ] **Step 3: Update the tracked YAML and README**

Replace its controller section with:

```yaml
controller:
  kind: threshold_staggered_active
  threshold_percentage: 50.0
```

Replace the logging timestamp mapping's existing `timezone: utc` entry with:

```yaml
timestamp:
  key: logged_at
  format: iso
  utc: true
```

Document this setup sequence in the README:

```python
config = load_config(Path("configs/default.yaml"))
configure_logging(config.logging)
environment = Environment(config.environment)
controller = build_controller(config.controller)
```

State that configuration is loaded once at setup and passed explicitly, not held in a global singleton.

- [ ] **Step 4: Run complete verification**

Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `git diff --check`. Expect all checks to pass.

- [ ] **Step 5: Commit the task**

Run `git add configs/default.yaml README.md tests/configuration/test_loader.py`, then run `git commit -m "docs: document configuration setup"`.
