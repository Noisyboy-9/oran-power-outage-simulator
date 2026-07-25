# Single-Use Simulation Metric Collection Design

## Scope

`Simulation.simulate()` is a single-use operation. Remove the state that made
initial metric collection idempotent across repeated calls. No Environment or
metric-service APIs change.

## Design

`Simulation` will no longer store `_initial_metrics_collected`. Its initial
collection helper will always call every configured collector with the current
environment and timestamp. Because a newly created simulation starts at
timestamp `0`, the first call to `simulate()` continues to record the required
initial observation before any environment update.

The existing comment explaining why the initial state is collected remains.
The public contract does not support calling `simulate()` more than once;
therefore no repeat-call guard is needed.

## Testing

Update the simulation test so it verifies a single run collects timestamps
`0` through `steps` and preserves the update-then-collect ordering. Remove the
test assertions that described a second `simulate()` call as supported.
