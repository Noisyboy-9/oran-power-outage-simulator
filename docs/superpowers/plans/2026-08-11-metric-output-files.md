# Metric Output Files Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write one self-contained JSON result file per configured metric collector after a simulation, containing the complete input configuration, timestamped observations, and final metric value.

**Architecture:** `MetricCollector` owns the shared file contract: it finalizes its result, serializes the complete immutable `ApplicationConfig`, converts infinity to JSON `null`, and atomically replaces its named output file. Each concrete collector only turns its retained observations into JSON-ready records. `main.py` accepts the required directory path and invokes each collector's output method after `Simulation.simulate()` returns.

**Tech Stack:** Python 3.12 standard library (`dataclasses`, `json`, `math`, `pathlib`, `tempfile`), pytest, Ruff, uv.

## Global Constraints

- Add the required CLI option exactly as `--metrics-output-path PATH`; argparse exposes it as `arguments.metrics_output_path`.
- Use one indented UTF-8 JSON file per selected collector, directly in the requested directory, whose name is the collector's stable name followed by `.json`.
- Create missing output directories; atomically replace an existing same-named output file.
- Put the complete loaded `ApplicationConfig` in the first top-level JSON member, named `input_configuration`.
- Use top-level member order: `input_configuration`, `collector`, `observations`, `final_result`.
- Write `final_result` as a JSON number when finite and as the JSON literal `null` only when the calculated value is `float("inf")`; never write the string `"null"`.
- Do not write a result file before a collector has at least one observation, do not write during time steps, and do not modify the environment.
- Keep current metric definitions, public collector names, timestamp validation, and `finish_calculation() -> float` behavior unchanged.
- Add no dependencies; run commands through `uv`.

---

## File Structure

- Modify `src/simulator/metrics/base.py`: add the shared collector-output interface, configuration serialization, JSON document construction, finite/infinite encoding, and atomic file replacement.
- Modify `src/simulator/metrics/average_emergency_qos.py`: expose timestamp-ordered served-user observations for JSON output.
- Modify `src/simulator/metrics/average_ru_battery_depletion_time.py`: expose timestamp-ordered RU battery snapshots for JSON output.
- Modify `src/simulator/metrics/network_lifetime.py`: expose timestamp-ordered served-user observations for JSON output.
- Modify `tests/metrics/conftest.py`: provide a complete reusable application-configuration test helper.
- Modify `tests/metrics/test_base.py`: cover the common JSON output contract, including full configuration, directory creation, overwrite behavior, null-for-infinity encoding, and rejection before observation.
- Modify `tests/test_simulation.py`: satisfy the new abstract observation-record interface in simulation-only test doubles.
- Modify `tests/metrics/test_average_emergency_qos.py`, `tests/metrics/test_average_ru_battery_depletion_time.py`, and `tests/metrics/test_network_lifetime.py`: verify each collector's distinct observation records.
- Modify `main.py` and `tests/test_main.py`: require and forward the output-directory argument, then write outputs after simulation.
- Modify `README.md`: document invocation, output layout, observation formats, and the exact meaning of `final_result: null`.

### Task 1: Add the Shared Collector JSON Output Contract

**Files:**
- Modify: `src/simulator/metrics/base.py`
- Modify: `tests/metrics/test_base.py`
- Modify: `tests/metrics/conftest.py`
- Modify: `tests/test_simulation.py`

**Interfaces:**
- Consumes: `ApplicationConfig` and the concrete collector's existing observation state.
- Produces: `MetricCollector.write_output(output_directory: Path, config: ApplicationConfig) -> Path`.
- Produces: abstract `MetricCollector._observation_records() -> list[dict[str, object]]` for concrete collectors.
- Consumed by: the three concrete collectors in Task 2 and `main.main()` in Task 3.

- [ ] **Step 1: Write failing common-output tests**

  In `tests/metrics/conftest.py`, add `make_application_config()` so all metric
  test modules can build a complete, real `ApplicationConfig`. It must contain
  an `EnvironmentConfig` with `MapConfig(width=2, height=2)`, one active
  `RUConfig`, one user, `random_seed=7`, an `ALWAYS_ACTIVE` controller, complete
  `LoggingConfig`/`TimestampConfig`, and a one-collector `MetricsConfig`:

  ```python
  def make_application_config() -> ApplicationConfig:
      return ApplicationConfig(
          environment=EnvironmentConfig(
              map=MapConfig(width=2, height=2),
              ru=RUConfig(
                  count=1,
                  initial_battery=10.0,
                  initial_status=RUStatus.ACTIVE,
                  zero_user_consumption=1.0,
                  one_user_consumption=2.0,
                  multi_user_consumption_per_user=1.5,
                  sleep_consumption=0.5,
                  coverage_radius=1.0,
              ),
              user_count=1,
              random_seed=7,
          ),
          controller=ControllerConfig(kind=ControllerKind.ALWAYS_ACTIVE),
          logging=LoggingConfig(
              logger_name="test",
              level=20,
              destination="stdout",
              format="json",
              include_logger_name=False,
              include_log_level=False,
              timestamp=TimestampConfig(key="logged_at", format="iso", utc=True),
              cache_loggers_on_first_use=False,
              propagate=False,
          ),
          simulation=SimulationConfig(
              steps=1,
              metrics=MetricsConfig(
                  collectors=(MetricKind.AVERAGE_EMERGENCY_QOS,),
                  minimum_emergency_service_fraction=0.5,
                  minimum_service_link_weight=0.0,
              ),
          ),
      )
  ```

  Import the configuration/domain classes used above in `conftest.py`. In
  `tests/metrics/test_base.py`, import `json`, `Path`, and that helper from
  `conftest`.

  In `tests/test_simulation.py`, add this no-output implementation to both
  `RecordingCollector` and `LifecycleCollector`; they exercise simulation
  orchestration only and never call `write_output()`:

  ```python
  def _observation_records(self) -> list[dict[str, object]]:
      return []
  ```

  Extend `RecordingCollector` with `_observation_records()` that returns its
  timestamp list as `[{"timestamp": timestamp}]`. Add an `InfiniteCollector`
  whose `finish_calculation()` calls `_require_observation()` then returns
  `float("inf")`, and whose observation records are empty. Add these tests:

  ```python
  def test_write_output_creates_self_contained_json_and_replaces_existing_file(
      tmp_path: Path,
  ) -> None:
      collector = RecordingCollector()
      collector.collect(object(), 0)  # type: ignore[arg-type]
      collector.collect(object(), 1)  # type: ignore[arg-type]
      output_directory = tmp_path / "nested" / "results"
      output_path = output_directory / "recording.json"
      output_directory.mkdir(parents=True)
      output_path.write_text("stale", encoding="utf-8")

      assert (
          collector.write_output(output_directory, make_application_config())
          == output_path
      )

      payload = json.loads(output_path.read_text(encoding="utf-8"))
      assert list(payload) == ["input_configuration", "collector", "observations", "final_result"]
      assert payload["input_configuration"]["environment"]["random_seed"] == 7
      assert payload["collector"] == "recording"
      assert payload["observations"] == [{"timestamp": 0}, {"timestamp": 1}]
      assert payload["final_result"] == 2.0
  ```

  Add these boundary tests. Do not assert an implementation-specific temporary
  file name:

  ```python
  def test_write_output_creates_missing_directory(tmp_path: Path) -> None:
      collector = RecordingCollector()
      collector.collect(object(), 0)  # type: ignore[arg-type]

      output_path = collector.write_output(
          tmp_path / "new" / "results", make_application_config()
      )

      assert output_path.is_file()


  def test_write_output_rejects_an_unobserved_collector(tmp_path: Path) -> None:
      output_directory = tmp_path / "results"

      with pytest.raises(ValueError, match="cannot finish"):
          RecordingCollector().write_output(output_directory, make_application_config())

      assert not output_directory.exists()


  def test_write_output_encodes_an_infinite_result_as_json_null(tmp_path: Path) -> None:
      collector = InfiniteCollector()
      collector.collect(object(), 0)  # type: ignore[arg-type]

      payload = json.loads(
          collector.write_output(tmp_path, make_application_config()).read_text(
              encoding="utf-8"
          )
      )

      assert payload["final_result"] is None
  ```

- [ ] **Step 2: Run the focused tests to verify they fail**

  Run: `uv run pytest tests/metrics/test_base.py -v`

  Expected: FAIL because `MetricCollector` has neither `write_output()` nor
  `_observation_records()`. The existing timestamp and abstract-interface tests
  should continue to collect successfully after the test subclass gains the new
  abstract implementation.

- [ ] **Step 3: Implement shared document generation and atomic replacement**

  In `src/simulator/metrics/base.py`, import `asdict`, `json`, `math`, `Path`,
  `NamedTemporaryFile`, and `ApplicationConfig`. Add the abstract method:

  ```python
  @abstractmethod
  def _observation_records(self) -> list[dict[str, object]]:
      """Return timestamp-ordered JSON-ready observations for this metric."""
  ```

  Add this public method after `finish_calculation()`:

  ```python
  def write_output(self, output_directory: Path, config: ApplicationConfig) -> Path:
      self._require_observation()
      result = self.finish_calculation()
      output_directory.mkdir(parents=True, exist_ok=True)
      output_path = output_directory / f"{self.name}.json"
      payload = {
          "input_configuration": asdict(config),
          "collector": self.name,
          "observations": self._observation_records(),
          "final_result": None if math.isinf(result) else result,
      }
      temporary_path: Path | None = None
      try:
          with NamedTemporaryFile(
              mode="w",
              encoding="utf-8",
              dir=output_directory,
              prefix=f".{self.name}-",
              suffix=".tmp",
              delete=False,
          ) as temporary_file:
              temporary_path = Path(temporary_file.name)
              json.dump(payload, temporary_file, indent=2, allow_nan=False)
              temporary_file.write("\n")
          temporary_path.replace(output_path)
      except Exception:
          if temporary_path is not None:
              temporary_path.unlink(missing_ok=True)
          raise
      return output_path
  ```

  Keep the root dictionary literal in this order so `input_configuration` is
  physically first in the file. The shown `except` block removes an
  already-created temporary file if dumping or replacement raises, then
  re-raises the original exception. Do not catch directory-creation or other
  output errors at this layer.

- [ ] **Step 4: Run the common-output tests to verify they pass**

  Run: `uv run pytest tests/metrics/test_base.py -v`

  Expected: PASS. Confirm the decoded payload uses a full nested configuration,
  the exact top-level order, a numeric finite result, and Python `None` for the
  JSON literal `null` infinite result.

- [ ] **Step 5: Commit the shared output contract**

  ```bash
  git add src/simulator/metrics/base.py tests/metrics/conftest.py tests/metrics/test_base.py tests/test_simulation.py
  git commit -m "feat: add metric JSON output contract"
  ```

### Task 2: Serialize Each Collector's Existing Observations

**Files:**
- Modify: `src/simulator/metrics/average_emergency_qos.py`
- Modify: `src/simulator/metrics/average_ru_battery_depletion_time.py`
- Modify: `src/simulator/metrics/network_lifetime.py`
- Modify: `tests/metrics/test_average_emergency_qos.py`
- Modify: `tests/metrics/test_average_ru_battery_depletion_time.py`
- Modify: `tests/metrics/test_network_lifetime.py`

**Interfaces:**
- Consumes: `MetricCollector._observation_records()` from Task 1 and the
  existing `_served_fractions` or `_battery_snapshots` dictionaries.
- Produces: JSON-ready timestamp-ordered observation records in the three
  formats specified by the approved design.
- Consumed by: `MetricCollector.write_output()` from Task 1.

- [ ] **Step 1: Write failing concrete-observation tests**

  In each collector test module, import `json`, `Path`, and
  `make_application_config` from `conftest`; then collect two or more known
  states, call `write_output(tmp_path, make_application_config())`, decode the
  file, and assert only the metric-specific records. Add these tests:

  ```python
  def test_average_emergency_qos_writes_served_fraction_observations(
      tmp_path: Path,
  ) -> None:
      collector = AverageEmergencyQoSCollector(minimum_service_link_weight=0.3)
      collector.collect(make_environment(2), 0)
      collector.collect(make_environment(1), 1)

      output_path = collector.write_output(tmp_path, make_application_config())
      payload = json.loads(output_path.read_text(encoding="utf-8"))

      assert payload["observations"] == [
          {"timestamp": 0, "served_user_fraction": 1.0},
          {"timestamp": 1, "served_user_fraction": 0.5},
      ]
  ```

  Add this network-lifetime record test:

  ```python
  def test_network_lifetime_writes_served_fraction_observations(
      tmp_path: Path,
  ) -> None:
      collector = NetworkLifetimeCollector(
          minimum_emergency_service_fraction=0.5,
          minimum_service_link_weight=0.3,
      )
      collector.collect(make_environment(2), 0)
      collector.collect(make_environment(1), 1)

      output_path = collector.write_output(tmp_path, make_application_config())
      payload = json.loads(output_path.read_text(encoding="utf-8"))

      assert payload["observations"] == [
          {"timestamp": 0, "served_user_fraction": 1.0},
          {"timestamp": 1, "served_user_fraction": 0.5},
      ]
  ```

  Add this battery record test:

  ```python
  def test_average_ru_battery_depletion_time_writes_battery_observations(
      tmp_path: Path,
  ) -> None:
      environment = make_environment()
      collector = AverageRUBatteryDepletionTimeCollector()
      collector.collect(environment, 0)
      set_batteries(environment, {1: 0.0, 2: 1.0})
      collector.collect(environment, 1)

      output_path = collector.write_output(tmp_path, make_application_config())
      payload = json.loads(output_path.read_text(encoding="utf-8"))

      assert payload["observations"] == [
          {"timestamp": 0, "ru_batteries": {"1": 2.0, "2": 3.0}},
          {"timestamp": 1, "ru_batteries": {"1": 0.0, "2": 1.0}},
      ]
  ```

  Add these independent infinity-output tests; keep the existing calculation
  tests unchanged:

  ```python
  def test_average_ru_battery_depletion_time_writes_null_for_infinity(
      tmp_path: Path,
  ) -> None:
      environment = make_environment()
      collector = AverageRUBatteryDepletionTimeCollector()
      collector.collect(environment, 0)

      output_path = collector.write_output(tmp_path, make_application_config())
      payload = json.loads(output_path.read_text(encoding="utf-8"))

      assert payload["final_result"] is None
  ```

  ```python
  def test_network_lifetime_writes_null_for_infinity(tmp_path: Path) -> None:
      collector = NetworkLifetimeCollector(
          minimum_emergency_service_fraction=0.5,
          minimum_service_link_weight=0.3,
      )
      collector.collect(make_environment(1), 0)

      output_path = collector.write_output(tmp_path, make_application_config())
      payload = json.loads(output_path.read_text(encoding="utf-8"))

      assert payload["final_result"] is None
  ```

- [ ] **Step 2: Run concrete collector tests to verify they fail**

  Run: `uv run pytest tests/metrics/test_average_emergency_qos.py tests/metrics/test_average_ru_battery_depletion_time.py tests/metrics/test_network_lifetime.py -v`

  Expected: FAIL because the concrete collectors do not implement the new
  abstract `_observation_records()` method and therefore cannot be instantiated.

- [ ] **Step 3: Implement timestamp-ordered records without changing calculations**

  Add `_observation_records()` to `AverageEmergencyQoSCollector` and
  `NetworkLifetimeCollector`:

  ```python
  def _observation_records(self) -> list[dict[str, object]]:
      return [
          {"timestamp": timestamp, "served_user_fraction": served_fraction}
          for timestamp, served_fraction in sorted(self._served_fractions.items())
      ]
  ```

  Add `_observation_records()` to `AverageRUBatteryDepletionTimeCollector`:

  ```python
  def _observation_records(self) -> list[dict[str, object]]:
      return [
          {
              "timestamp": timestamp,
              "ru_batteries": {str(ru_id): battery for ru_id, battery in snapshot.items()},
          }
          for timestamp, snapshot in sorted(self._battery_snapshots.items())
      ]
  ```

  Preserve the existing dictionaries, collection sequence, and
  `finish_calculation()` implementations exactly. Do not add collector-specific
  file-writing code.

- [ ] **Step 4: Run concrete collector tests to verify they pass**

  Run: `uv run pytest tests/metrics/test_average_emergency_qos.py tests/metrics/test_average_ru_battery_depletion_time.py tests/metrics/test_network_lifetime.py -v`

  Expected: PASS. The JSON records are sorted by timestamp, fractions are JSON
  numbers, battery keys are strings, and both current infinite-result scenarios
  decode as `None`.

- [ ] **Step 5: Commit concrete observation serialization**

  ```bash
  git add src/simulator/metrics/average_emergency_qos.py src/simulator/metrics/average_ru_battery_depletion_time.py src/simulator/metrics/network_lifetime.py tests/metrics/test_average_emergency_qos.py tests/metrics/test_average_ru_battery_depletion_time.py tests/metrics/test_network_lifetime.py
  git commit -m "feat: serialize metric collector observations"
  ```

### Task 3: Require the Output Path at Application Startup

**Files:**
- Modify: `main.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: `MetricCollector.write_output(output_directory: Path, config: ApplicationConfig) -> Path` from Task 1.
- Produces: a required `--metrics-output-path PATH` CLI option and one output-method call per configured collector after `simulation.simulate()`.
- Consumed by: command-line users documented in Task 4.

- [ ] **Step 1: Write failing CLI and orchestration tests**

  In `tests/test_main.py`, rename the first test to
  `test_requires_configs_and_metrics_output_path_arguments` and parameterize the
  missing-argument invocations `[]`, `["--configs", "example.yaml"]`, and
  `["--metrics-output-path", "outputs"]`. Each must raise `SystemExit` with
  code `2` before `load_config` is called.

  Replace `FakeCollector.finish_calculation()` in the orchestration test with:

  ```python
  def write_output(self, output_directory: Path, config: object) -> Path:
      events.append(("write_output", self.name, output_directory, config))
      return output_directory / f"{self.name}.json"
  ```

  Invoke `main.main()` with both flags and expect the two `write_output` events
  after `"simulate"`, in configured collector order, each receiving
  `Path("outputs")` and the same loaded config object. Update the
  configuration-error test invocation to include `--metrics-output-path
  outputs` so it continues to exercise configuration loading rather than CLI
  validation.

- [ ] **Step 2: Run entry-point tests to verify they fail**

  Run: `uv run pytest tests/test_main.py -v`

  Expected: FAIL because `--metrics-output-path` is unknown and `main.py` still
  calls `finish_calculation()` instead of `write_output()`.

- [ ] **Step 3: Parse and forward the required directory**

  In `_parse_arguments()`, add:

  ```python
  parser.add_argument(
      "--metrics-output-path",
      required=True,
      metavar="PATH",
      help="directory where metric JSON files are written",
  )
  ```

  After `simulation.simulate()`, replace the current `finish_calculation()`
  loop with:

  ```python
  output_directory = Path(arguments.metrics_output_path)
  for collector in metric_collectors:
      collector.write_output(output_directory, config)
  ```

  Do not create the directory in `main.py`; no configured collectors means no
  writer call and therefore no output directory creation.

- [ ] **Step 4: Run entry-point tests to verify they pass**

  Run: `uv run pytest tests/test_main.py -v`

  Expected: PASS. The parser rejects either absent required option, no
  application component starts on argument failure, and the fake collectors are
  written only after the fake simulation records completion.

- [ ] **Step 5: Commit CLI output integration**

  ```bash
  git add main.py tests/test_main.py
  git commit -m "feat: require metric output directory"
  ```

### Task 4: Publish the File Contract and Verify the Repository

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the implemented CLI and JSON contract from Tasks 1–3.
- Produces: user-facing invocation and JSON-output documentation.

- [ ] **Step 1: Update the README metrics documentation**

  Replace the running command with:

  ```bash
  uv run python main.py --configs configs/default.yaml --metrics-output-path outputs/run-001
  ```

  After the Metrics section, add a concise `### Metric output files` subsection
  that lists the three possible names, states that only selected collectors
  write files, and says the complete input configuration is the first JSON
  member. Use this exact, compact result-body example after explaining that the
  preceding `input_configuration` member contains the full loaded configuration:

  ```json
  {
    "collector": "average_emergency_qos",
    "observations": [{"timestamp": 0, "served_user_fraction": 1.0}],
    "final_result": 1.0
  }
  ```

  State explicitly that `final_result` is a JSON number when finite and the
  JSON literal `null` when the calculated value is infinite; `"null"` is never
  written. Document the battery observation's `ru_batteries` map and its
  string RU-ID keys, plus overwrite behavior for repeated runs using the same
  directory.

- [ ] **Step 2: Run the full test suite**

  Run: `uv run pytest`

  Expected: PASS. This confirms the new output interface is implemented by all
  concrete collectors and all existing simulation, configuration, metric, and
  entry-point behavior remains compatible.

- [ ] **Step 3: Run lint and formatting checks**

  Run: `uv run ruff check .`

  Expected: PASS.

  Run: `uv run ruff format --check .`

  Expected: PASS.

- [ ] **Step 4: Inspect the final change set**

  Run: `git status --short`

  Expected: only `README.md` and the task's intentional source/test changes if
  Task 1–3 commits were not made; no cache, virtual-environment, output JSON,
  or unrelated file is present.

  Run: `git diff --check HEAD~3..HEAD`

  Expected: no whitespace errors across the three implementation commits. If
  commits were squashed or additional intentional commits exist, use
  `git diff --check HEAD` instead.

- [ ] **Step 5: Commit the documentation**

  ```bash
  git add README.md
  git commit -m "docs: describe metric output files"
  ```
