# RU–User Association Design

## Goal

Make each user associate with at most one radio unit (RU). A user ranks the
nearby, currently available RUs by connection quality and requests them in
that order. An RU accepts requests until its configured user capacity is full;
the user then tries the next candidate. Sleeping or battery-depleted RUs are
not candidates.

This design is deliberately layered on top of the preceding RU user-load
battery-consumption change. It replaces that change's non-exclusive
RU–user-link interpretation with an exclusive association wherever user
service or user load is calculated.

## Configuration and Domain State

The preceding change replaces `active_consumption` with
`zero_user_consumption`, `one_user_consumption`, and
`multi_user_consumption_per_user`. This change retains those names and adds
one required `user_capacity: int` setting to the uniform `RUConfig`.
`user_capacity` must be a non-boolean positive integer and is added to the
YAML schema and default configuration.

Each `RU` stores its positive integer `user_capacity`. It does not store
current users or decide whether to accept them: membership changes are
environment-wide state, and capacity requires coordinated decisions across all
users. The environment remains the only owner of the association mapping.

## Association Algorithm

`Environment` owns a private mapping from every owned `User` to either its
owned associated `RU` or `None`. It exposes this narrow query:

```python
get_associated_ru(user: User) -> RU | None
```

As with `get_connection_weight`, a foreign user object returns `None` even if
it compares equal to an owned user. No mutable mapping is exposed publicly.

The environment rebuilds the complete mapping immediately after it builds the
connectivity graph during construction, and after every updated connectivity
graph during a simulation step. A rebuild starts with all RUs having zero
accepted users, then processes users by ascending ID. For each user, it
considers only RUs that:

1. have an edge to the user in the current connectivity graph;
2. are `ACTIVE`;
3. have battery strictly greater than zero; and
4. still have fewer accepted users than `user_capacity`.

Candidates are ordered by descending edge weight, with ascending RU ID as the
tie-breaker. The first eligible candidate is recorded; if every candidate is
full or unavailable, the user maps to `None`. Because each user is processed
once and only one result is recorded, an association is exclusive. Ordering by
user and RU ID makes capacity contention reproducible for a fixed graph.

The mapping is intentionally recomputed rather than persisted. Existing
connectivity weights are regenerated each timestep, and controller decisions
may make an RU unavailable; a fresh mapping represents the current timestep
without introducing session, handover, or retry state.

## Step Timing and Load-Aware Battery Integration

After the preceding battery change is merged, the update order is:

1. charge batteries from the existing graph and prior association mapping;
2. apply the RU controller;
3. rebuild the connectivity graph; and
4. rebuild the association mapping from the new graph and statuses.

Thus, the load charged at a step describes associations that existed during the
just-completed timestep. The association visible to metrics after the update
is based on the newly selected RU statuses and graph.

The existing `minimum_service_link_weight` remains the single configured
service-quality threshold. It continues to be supplied to
`Environment.update()` by `Simulation`. For a particular RU, its
`serviced_user_count` becomes the number of users associated with that RU
whose current association edge exists and meets that threshold. It no longer
counts every qualifying graph edge. An association below the threshold still
uses one capacity slot but does not count as service or load under the
load-aware battery model; this preserves the preceding change's threshold
semantics.

## Service Metrics

The shared service helper no longer searches every RU for each user. It looks
up the user's associated RU, then requires that one RU to be active, have
positive battery, retain its graph edge, and meet
`minimum_service_link_weight`. An unassociated user is not served. This makes
Average Emergency QoS and Network Lifetime observe the same exclusive model
as capacity and battery load.

## Testing

Tests will cover:

- `RU` and `RUConfig` acceptance of a positive `user_capacity` and rejection
  of zero, negatives, booleans, and non-integers;
- YAML loading of the new required capacity field and rejection of invalid,
  missing, and unknown keys;
- selection of the highest-weight eligible RU;
- fallback to the next-ranked RU when the first is full;
- one association per user, capacity limits, deterministic user/RU tie breaks,
  and no association when every candidate is unavailable or full;
- exclusion of sleeping and depleted RUs during construction and after an
  update;
- calculation of RU load from associated qualifying users rather than all
  qualifying graph edges; and
- service metrics rejecting an otherwise valid non-associated RU connection.

All tests remain deterministic by directly constructing controlled graphs
where association choice matters. The complete pytest suite, Ruff lint, Ruff
format check, and Git whitespace check are required before completion.

## Scope Boundaries

This change adds no mobility, per-user demand, handover persistence, custom
acceptance policies, heterogeneous RU capacities, or external admission
logic. It does not alter connectivity edge generation, controller scheduling,
the meaning of `minimum_service_link_weight`, or result formatting.
