import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from simulator.configuration import ConfigurationError, load_config
from simulator.logging import configure_logging
from simulator.metrics import build_metric_collectors
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
    metric_collectors = build_metric_collectors(config.simulation.metrics)
    simulation = Simulation(config, metric_collectors=metric_collectors)
    simulation.simulate()
    for collector in metric_collectors:
        collector.finish_calculation()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
