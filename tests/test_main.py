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
    metrics_config = object()
    config = SimpleNamespace(
        logging=logging_config,
        simulation=SimpleNamespace(metrics=metrics_config),
    )

    class FakeCollector:
        def __init__(self, name: str) -> None:
            self.name = name

        def finish_calculation(self) -> float:
            events.append(f"finish:{self.name}")
            return 0.0

    fake_collectors = [FakeCollector("first"), FakeCollector("second")]

    def fake_load_config(path: Path) -> object:
        events.append(("load", path))
        return config

    def fake_configure_logging(received_config: object) -> None:
        events.append(("configure_logging", received_config))

    def fake_build_metric_collectors(received_config: object) -> list[FakeCollector]:
        events.append(("build_collectors", received_config))
        return fake_collectors

    class FakeSimulation:
        def __init__(
            self, received_config: object, *, metric_collectors: object
        ) -> None:
            events.append(("construct", received_config, metric_collectors))

        def simulate(self) -> None:
            events.append("simulate")

    monkeypatch.setattr(main, "load_config", fake_load_config)
    monkeypatch.setattr(main, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(
        main,
        "build_metric_collectors",
        fake_build_metric_collectors,
        raising=False,
    )
    monkeypatch.setattr(main, "Simulation", FakeSimulation)

    assert main.main(["--configs", "example.yaml"]) == 0
    assert events == [
        ("load", Path("example.yaml")),
        ("configure_logging", logging_config),
        ("build_collectors", metrics_config),
        ("construct", config, fake_collectors),
        "simulate",
        "finish:first",
        "finish:second",
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
        "error: simulation.steps: must be a positive integer\n"
    )
    assert configured_logging is False
    assert constructed_simulation is False
