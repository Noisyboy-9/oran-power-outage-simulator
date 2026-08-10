# RU–User Association Design

## Goal

Make each user associate with at most one radio unit (RU). A user ranks the
nearby, currently available RUs by connection quality and requests them in
that order. An RU accepts requests until its configured user capacity is full;
the user then tries the next candidate. Sleeping or battery-depleted RUs are
skipped and never contacted.

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

## Environment State Representation

The environment owns exactly two related structures; it does **not** own two
graphs:

| Structure | Contains | Answers |
| --- | --- | --- |
| Connectivity graph | Every in-range RU–user pair and its connection-weight edge | Which RUs could a user connect to, and how good is each possible link? |
| Association map | One `User -> RU | None` result for every user | Which RU, if any, actually accepted this user? |

The connectivity graph is the set of options. It is unchanged by capacity and
may contain many edges for one user. The association map is the final admission
decision. It is not a graph because every user has at most one accepted RU; a
mapping is smaller, directly expresses that invariant, and avoids duplicating
edge weights and topology.

The association map never creates a connection-quality value. Whenever a
consumer needs quality, it reads the edge for the selected RU from the
connectivity graph.

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
graph during a simulation step. The rebuild receives the configured
`minimum_service_link_weight`; it is the same threshold already passed from
`Simulation` to `Environment.update()`. The environment stores no duplicate
configuration field.

A rebuild starts with all RUs having zero accepted users, then processes users
by ascending ID. The user constructs its candidate list by considering only
RUs that:

1. have an edge to the user in the current connectivity graph;
2. have edge weight greater than or equal to
   `minimum_service_link_weight`.

Candidates are ordered by descending edge weight, with ascending RU ID as the
tie-breaker. The user considers that ordered list in turn. It skips sleeping or
battery-depleted RUs, and sends an association request to every remaining
candidate. A requested RU accepts when it has fewer accepted users than
`user_capacity`; a full RU rejects the request and the user tries the next
candidate. The first accepted RU is recorded; if every candidate is
unavailable or full, the user maps to `None`. Because each user is processed
once and only one result is recorded, an association is exclusive. Ordering by
user and RU ID makes capacity contention reproducible for a fixed graph.

An RU whose edge weight is below `minimum_service_link_weight` is omitted from
the candidate list and is never contacted. A user with no qualifying candidate
is unassociated and therefore unserved. A user whose qualifying candidates are
all full is also unassociated and unserved. An edge whose weight exactly equals
the threshold is qualifying, matching the project's established inclusive
threshold semantics.

The mapping is intentionally recomputed rather than persisted. Existing
connectivity weights are regenerated each timestep, and controller decisions
may make an RU unavailable; a fresh mapping represents the current timestep
without introducing session, handover, or retry state.

The resulting information flow is:

```text
connectivity graph (possible weighted links)
    -> rank available candidates and apply capacity
    -> association map (one accepted RU or None per user)
    -> service metrics and RU user-load charging
```

## Step Timing and Load-Aware Battery Integration

`Simulation` passes the existing
`config.simulation.metrics.minimum_service_link_weight` when it constructs
`Environment`, allowing the environment to create associations before initial
`t=0` metric collection. It continues to pass that same threshold to every
`Environment.update()` call.

The update order is:

1. charge batteries from the existing graph and prior association mapping;
2. apply the RU controller;
3. rebuild the connectivity graph of possible links; and
4. rebuild the association mapping from the new graph, statuses, capacities,
   and service-link threshold.

Thus, the load charged at a step describes associations that existed during the
just-completed timestep. The association visible to metrics after the update
is based on the newly selected RU statuses and graph.

The existing `minimum_service_link_weight` is the single configured
service-quality and admission threshold. For a particular RU, its
`serviced_user_count` becomes the number of users associated with that RU. It
does not count every qualifying graph edge. Every association already met the
threshold when it was created, so a low-quality link cannot reserve capacity,
count as service, or add load to an RU.

## Service Metrics

Currently, the shared service helper searches all RUs for each user and counts
the user as served when *any* RU has a usable qualifying graph edge. It counts
the user only once, but it does not record which RU supplied that service.

The association-aware helper instead performs one association-map lookup per
user. An unassociated user is not served. For an associated user, it checks
only the selected RU: the connectivity graph must still contain that edge, the
RU must be active with positive battery, and the edge weight must meet
`minimum_service_link_weight`. It never searches alternative RUs. This makes
Average Emergency QoS and Network Lifetime observe the same exclusive model as
capacity and battery load.

The helper must still check graph-edge presence separately. A zero service-link
threshold accepts every existing association edge but must not turn the
`get_connection_weight()` no-edge sentinel (`0.0`) into service. Looking up an
association is a read-only operation: collectors never create, repair, or
recompute associations.

`AverageEmergencyQoSCollector` and `NetworkLifetimeCollector` keep their
current public constructors, timestamp observations, result calculations, and
factory wiring. Their observed served-user fractions change solely through the
shared helper. `AverageRUBatteryDepletionTimeCollector` remains association
agnostic: it reads only RU batteries, so it needs no production-code change.
Metric collector collection must continue not to mutate either RU state,
connectivity, or the association mapping.

## Testing

Tests will cover:

- `RU` and `RUConfig` acceptance of a positive `user_capacity` and rejection
  of zero, negatives, booleans, and non-integers;
- YAML loading of the new required capacity field and rejection of invalid,
  missing, and unknown keys;
- selection of the highest-weight eligible RU;
- exclusion of below-threshold RUs from a user's candidate list, including an
  edge exactly at the threshold;
- fallback to the next-ranked qualifying RU when the first is full;
- one association per user, capacity limits, deterministic user/RU tie breaks,
  and no association when every candidate is below threshold, unavailable, or
  full;
- exclusion of sleeping and depleted RUs during construction and after an
  update;
- initial `t=0` association creation using the configured threshold;
- calculation of RU load from associated users rather than all qualifying
  graph edges; and
- service metrics rejecting an otherwise valid non-associated RU connection,
  an unassociated user, and an association whose link is below the threshold;
- Average Emergency QoS and Network Lifetime inheriting the association-aware
  served fraction without changes to their result formulas; and
- metric collection leaving the association mapping unchanged, while the
  battery-depletion collector continues to work without querying associations.

The README and default YAML configuration will document `user_capacity`, the
quality-filtered candidate list, and the distinction between potential graph
links and actual associations. They will remove the current statement that one
user can be counted by multiple RUs.

All tests remain deterministic by directly constructing controlled graphs
where association choice matters. The complete pytest suite, Ruff lint, Ruff
format check, and Git whitespace check are required before completion.

## Scope Boundaries

This change adds no mobility, per-user demand, handover persistence, custom
acceptance policies, heterogeneous RU capacities, or external admission
logic. It does not alter connectivity edge generation, controller scheduling,
metric result formulas, or result formatting.
