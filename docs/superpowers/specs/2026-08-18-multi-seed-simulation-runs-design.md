# Multi-Seed Simulation Runs Design

## Goal

Run each supported controller policy under ten reproducible random seeds with
one `make run-all` command.  Keep the result files for every policy and seed
separate so comparative analysis can use all thirty simulation runs without
overwriting metrics.

## Configuration Layout

`configs/` will contain ten numbered iteration directories:

```text
configs/
├── default.yaml
├── iteration-01/
│   ├── always_active.yaml
│   ├── staggered_active.yaml
│   └── threshold_staggered_active.yaml
├── iteration-02/
│   ├── always_active.yaml
│   ├── staggered_active.yaml
│   └── threshold_staggered_active.yaml
├── iteration-03 through iteration-09/
│   └── (the same three policy files)
└── iteration-10/
    ├── always_active.yaml
    ├── staggered_active.yaml
    └── threshold_staggered_active.yaml
```

The three files in an iteration retain the same environment, logging, metrics,
and simulation settings as today.  Only their controller sections differ.
Each iteration uses one seed across all its policies, so a policy comparison
uses the same generated map, RU placement, user placement, and randomized link
weights.  The assigned seeds are the iteration numbers: `iteration-01` uses
`1`, through `iteration-10` using `10`.

`configs/default.yaml` remains available for the documented one-off command.
The existing flat policy-specific files are removed after their contents have
been placed in the iteration directories; the numbered hierarchy is the single
authoritative batch configuration set.

## Batch Command and Output Layout

`make run` remains the one-configuration command and continues to accept its
existing `CONFIG` and `METRICS_OUTPUT_PATH` overrides.

`make run-all` iterates in numeric iteration order and, within each iteration,
runs the policies in this stable order:

1. `always_active`
2. `staggered_active`
3. `threshold_staggered_active`

It invokes the existing `run` target once for every combination, for a total
of thirty simulations.  Every invocation passes its explicit configuration
path and an output directory in this layout:

```text
outputs/
├── iteration-01/
│   ├── always_active/
│   ├── staggered_active/
│   └── threshold_staggered_active/
├── iteration-03 through iteration-09/
│   └── (the same three policy output directories)
└── iteration-10/
    ├── always_active/
    ├── staggered_active/
    └── threshold_staggered_active/
```

Each leaf contains the existing metric JSON files directly:
`average_emergency_qos.json`, `average_ru_battery_depletion_time.json`, and
`network_lifetime.json`.  Those files already embed the complete input
configuration, including `environment.random_seed`, so the output remains
self-describing.

The target stops at the first failed simulation and returns that failure to
the caller.  It does not delete, aggregate, or otherwise alter output from
completed runs.  Re-running the same batch replaces only same-named metric
files in the corresponding leaf directories, following the existing atomic
per-metric write behavior.

## Makefile Structure

The Makefile will centralize the iteration identifiers and policy names in
variables, then use nested shell loops in `run-all`.  The loop calls
`$(MAKE) run` rather than duplicating the Python command, preserving one
source of truth for normal simulator execution.  The help text will describe
that `make run-all` runs all ten seeds and three policies, writing results
below `outputs/`.

## Testing and Documentation

Automated coverage will assert that:

- each of the ten iteration directories contains exactly the three policy
  configurations;
- every YAML configuration loads successfully;
- the policies within an iteration have identical random seeds;
- the ten iteration seeds are distinct and equal to `1` through `10`; and
- a dry run of `make run-all` expands to all thirty expected configuration and
  output-path pairs in the specified order.

The README will document the numbered configuration hierarchy, the purpose of
shared seeds across policies, `make run-all`, and the output directory layout.

## Scope Boundaries

This change does not alter the simulator's random-number implementation,
controller behavior, metric definitions, metrics JSON schema, or the
single-configuration command-line interface.  It adds no dependencies and
does not aggregate the thirty metric results into summary statistics.
