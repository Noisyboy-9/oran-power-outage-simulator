from pathlib import Path
from types import SimpleNamespace

import pytest

import main
from simulator.configuration import ConfigurationError


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--configs", "example.yaml"],
        ["--metrics-output-path", "outputs"],
    ],
)
def test_requires_configs_and_metrics_output_path_arguments(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
) -> None:
    load_config_called = False

    def fake_load_config(path: Path) -> object:
        nonlocal load_config_called
        load_config_called = True
        return object()

    monkeypatch.setattr(main, "load_config", fake_load_config)

    with pytest.raises(SystemExit) as error:
        main.main(arguments)

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

        def write_output(self, output_directory: Path, config: object) -> Path:
            events.append(("write_output", self.name, output_directory, config))
            return output_directory / f"{self.name}.json"

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

    assert (
        main.main(
            [
                "--configs",
                "example.yaml",
                "--metrics-output-path",
                "outputs",
            ]
        )
        == 0
    )
    assert events == [
        ("load", Path("example.yaml")),
        ("configure_logging", logging_config),
        ("build_collectors", metrics_config),
        ("construct", config, fake_collectors),
        "simulate",
        ("write_output", "first", Path("outputs"), config),
        ("write_output", "second", Path("outputs"), config),
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

    assert (
        main.main(
            [
                "--configs",
                "invalid.yaml",
                "--metrics-output-path",
                "outputs",
            ]
        )
        == 1
    )
    assert capsys.readouterr().err == (
        "error: simulation.steps: must be a positive integer\n"
    )
    assert configured_logging is False
    assert constructed_simulation is False
