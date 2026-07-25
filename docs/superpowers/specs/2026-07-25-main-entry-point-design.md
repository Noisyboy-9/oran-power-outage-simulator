# Main Entry Point Design

## Goal

Provide a repository-root `main.py` as the application composition root. It
loads one required configuration file, configures logging, constructs the
configured metric collectors, creates `Simulation`, and runs the configured
simulation to completion.

## Command-Line Interface

The application is invoked with:

```bash
uv run python main.py --configs path/to/config.yaml
```

`--configs` is a required flag despite its plural name. The standard-library
`argparse` module owns parsing, generated usage text, and the failure behavior
when the flag is absent or its value is missing. The application does not use a
default configuration path.

`main()` returns an integer process status and the module's `__main__` guard
exits with that status. A configuration file that cannot be loaded or fails
schema validation is reported as a concise error on standard error, and the
application exits nonzero before logging configuration or simulation
construction.

## Composition and Lifecycle

After parsing the configuration path, the entry point performs the following
operations in order:

1. Load `ApplicationConfig` with `load_config(Path(args.configs))`.
2. Configure structured logging with `configure_logging(config.logging)`.
3. Construct metric collectors from the configuration.
4. Create `Simulation(config, metric_collectors)`.
5. Call `simulation.simulate()` exactly once.

`Simulation.simulate()` owns the step loop and uses
`config.simulation.steps`; `main.py` must not read that value or implement its
own loop.

The current configuration schema has no metric section and no concrete metric
collector implementations. Therefore, the initial implementation passes an
empty collector iterable. When metric configuration is added, this composition
point will create the selected collector instances and pass them into
`Simulation`; it will not move collector selection into `Simulation` or add a
placeholder factory before there is a concrete metric configuration contract.

## Boundaries

`main.py` is responsible for command-line handling, configuration loading,
logging setup, metric collector construction, process status, and application
composition. It does not validate YAML itself, configure an environment or RU
controller directly, calculate metrics, own simulation state, or determine how
many steps to run.

`load_config` continues to own path-aware configuration validation;
`configure_logging` owns logging setup; `Simulation` owns all simulation state
and step ordering; and collector implementations own metric observation.

## Testing

Tests invoke `main()` with controlled argument lists and replace the external
composition dependencies at the module boundary. They verify:

- a missing `--configs` option is rejected by `argparse` before loading;
- a valid path is loaded, logging is configured, `Simulation` receives the
  loaded configuration and an empty collector iterable, and `simulate()` is
  called once in that order;
- a `ConfigurationError` prints a concise error to standard error and returns
  nonzero without configuring logging or constructing a simulation.

The README documents the required command and explains that `simulation.steps`
controls the run length.

## Scope Boundaries

This change adds neither a console-script package entry point nor third-party
CLI dependencies. It does not add metric configuration, concrete metrics,
signal handling, progress display, result persistence, a default configuration
path, or a duplicate simulation loop.
