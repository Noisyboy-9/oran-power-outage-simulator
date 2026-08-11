# Metric Output Files Design

## Goal

Persist the complete observation history and final result of every configured
metric collector as a self-contained JSON file after a simulation completes.
Each file must also contain the complete loaded application configuration so it
can be interpreted and reproduced without separately locating the YAML input.

## Command-Line Interface

`main.py` gains this required option:

```text
--metrics-output-path PATH
```

`PATH` names the directory where metric files are written. The directory is
created, including missing parents, when output is written. A caller must pass
the option even if configuration selects no collectors; in that case the
directory is not needed and no files are produced.

The normal invocation is:

```bash
uv run python main.py \
  --configs configs/default.yaml \
  --metrics-output-path outputs/run-001
```

## Output Contract

Each selected collector writes one file directly inside the output directory.
The collector's stable `name` determines the file name:

```text
average_emergency_qos.json
average_ru_battery_depletion_time.json
network_lifetime.json
```

Files are standard, indented UTF-8 JSON and use this top-level layout in the
listed order:

```json
{
  "input_configuration": {},
  "collector": "average_emergency_qos",
  "observations": [],
  "final_result": 0.75
}
```

`input_configuration` is the full loaded `ApplicationConfig`, converted to
JSON-compatible nested mappings and values. It is deliberately repeated in
every output file, making each file self-contained. Building the root mapping
in the shown order ensures the configuration block appears first in the written
JSON document.

The block includes every current configuration field, including an RU's
`user_capacity`. Configuration loading rejects non-finite numeric values before
simulation starts, ensuring the complete configuration is always valid standard
JSON. This leaves JSON `null` reserved exclusively for an infinite calculated
metric result.

`collector` is the collector's stable configuration name. `observations` is a
timestamp-ordered list of data the collector used. `final_result` is the
numeric value returned by the collector's existing `finish_calculation()`.

JSON has no representation for positive infinity. A collector whose calculated
result is `float("inf")` must write the JSON literal `null` as its sole final
result representation:

```json
"final_result": null
```

This is not the JSON string `"null"`. For a completed metric-output file,
`final_result: null` unambiguously means that the calculated result was
infinite. A file is never written for an unobserved or otherwise uncalculable
metric.

## Observation Shapes

The `observations` list preserves the data already collected by each collector:

- `average_emergency_qos` and `network_lifetime` write
  `{ "timestamp": <int>, "served_user_fraction": <float> }` for each
  timestamp.
- `average_ru_battery_depletion_time` writes
  `{ "timestamp": <int>, "ru_batteries": { "<ru id>": <float> } }` for each
  timestamp. JSON object keys are strings, so RU IDs are represented as their
  decimal-string form.

Timestamps begin at `0`, include every observed post-update state, and are
written in ascending order.

## Association Compatibility

The environment owns association admission. It maps every user to one accepted
RU or to `None`, using the configured link-weight threshold, RU availability,
and RU capacity. That association map—not a collector—defines whether a user
is served at a timestamp.

The output feature must remain observational. Average Emergency QoS and Network
Lifetime serialize the served-user fractions their existing association-aware
collector logic records; they must not re-evaluate graph edges, connection
weights, RU status, battery, capacity, or candidate selection while preparing
JSON records. Their output shape remains
`{ "timestamp": <int>, "served_user_fraction": <float> }`. Battery-depletion
output remains association-agnostic and serializes only the recorded RU battery
snapshots.

## Architecture and Flow

`MetricCollector` gains a public output method accepting an output directory
and the loaded application configuration. It calculates the final result,
creates the complete JSON document, and writes it to the collector's named
file. Concrete collectors provide only their metric-specific observation
records; the base collector owns the shared JSON layout, configuration
serialization, finite/infinite result encoding, and file-writing behavior.

`main.py` parses the required path, builds collectors as it does now, runs the
simulation, and then invokes the output method once for each collector. It no
longer discards bare return values from `finish_calculation()`.

Collectors remain observers: they do not write during a time step and never
modify the environment or its association map. Output happens only after the
simulation has finished.

## File Safety and Errors

Existing files with the same stable collector name are replaced, as requested.
Writing uses a temporary file in the target directory followed by an atomic
replacement, so a write failure does not leave a partial final JSON file. File
system failures (for example, an output path that is an existing regular file,
or a directory that cannot be created or written) are allowed to propagate to
the command-line entry point rather than being silently ignored.

## Tests and Documentation

Tests will verify:

- the required `--metrics-output-path` argument and its forwarding from
  `main.py`;
- creation of missing output directories and replacement of existing metric
  files;
- the complete configuration as the first top-level JSON entry;
- serialization of the current RU `user_capacity` configuration field;
- the specified observation shape and timestamp ordering for every collector;
- preservation of association-based served-user observations during output;
- finite output as a JSON number and infinite output as the JSON literal
  `null`; and
- no output before a collector has successfully observed data.

The README will document the mandatory command-line option, the output
directory layout, and the JSON contract, including the meaning of
`final_result: null`.
