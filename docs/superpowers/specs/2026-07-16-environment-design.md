# Environment Design

## Goal

Implement a fully initialized, static simulation environment that owns a
rectangular grid of square cells, uniformly configured radio units (RUs), users,
collision-free entity
placements, and a distance-limited weighted RU-to-user connectivity graph.

This change also replaces the existing `Point` domain model with an immutable
`MapCell` that combines Cartesian coordinates with optional occupancy.

## Package Structure

The environment becomes a package rather than a single module:

```text
src/simulator/
├── domain/
│   ├── map_cell.py
│   ├── ru.py
│   └── user.py
└── environment/
    ├── __init__.py
    ├── config.py
    ├── environment.py
    └── errors.py
```

`simulator.environment` publicly exports `Environment`, `EnvironmentConfig`,
`MapConfig`, `RUConfig`, and `EnvironmentValidationError`. The current empty
`src/simulator/environment.py` file is removed when the package is created.

## Domain Map Cell

`Point` is removed completely, including its module, tests, documentation, and
public export. No compatibility alias is retained.

`MapCell` is an immutable dataclass in `simulator.domain.map_cell`:

```python
@dataclass(frozen=True)
class MapCell:
    x: int
    y: int
    occupant: RU | User | None = None

    def distance_to(self, other: MapCell) -> float: ...
```

Coordinates must be non-negative integers. The occupant must be an `RU`, a
`User`, or `None`. Invalid values raise the existing `DomainValidationError`.
`distance_to()` returns the Euclidean Cartesian distance between two cells.

The map uses row-major indexing:

```text
environment_map[y][x] == MapCell(x=x, y=y, ...)
```

Map coordinates range from `(0, 0)` through `(width - 1, height - 1)`.
`MapCell` is the only location type; no separate `Point` or `Coordinate` type
exists.

## Configuration

Configuration is grouped into immutable dataclasses in
`simulator.environment.config`:

```python
@dataclass(frozen=True)
class MapConfig:
    width: int
    height: int


@dataclass(frozen=True)
class RUConfig:
    count: int
    initial_battery: float
    initial_status: RUStatus
    active_consumption: float
    sleep_consumption: float
    coverage_radius: float


@dataclass(frozen=True)
class EnvironmentConfig:
    map: MapConfig
    ru: RUConfig
    user_count: int
    random_seed: int | None = None
```

`MapConfig` requires positive integer width and height. `RUConfig` requires a
positive integer count and a positive coverage radius. `EnvironmentConfig`
requires `MapConfig` and `RUConfig` instances, requires a positive integer user
count, requires the total entity count not to exceed `width * height`, and
accepts only an integer or `None` as its random seed. Boolean values do not
count as integers for these validations. These environment configuration failures raise
`EnvironmentValidationError`, a new `ValueError` subclass in
`simulator.environment.errors`.

RU construction remains the authority for the validity of initial battery,
initial status, and consumption values. Invalid RU-specific values raise
`DomainValidationError` when an `Environment` creates its RUs, avoiding
duplicate RU validation rules in configuration code.

## Environment Construction

`Environment(config: EnvironmentConfig)` constructs the complete environment
immediately. There is no separate `setup()` method and no publicly observable
partially initialized state.

Construction follows this sequence:

1. Create a row-major map of empty `MapCell` instances.
2. Create `config.ru.count` RUs with IDs from `1` through the configured count,
   using the uniform RU settings.
3. Create `config.user_count` users with IDs from `1` through the configured
   count.
4. Use one private `random.Random(config.random_seed)` instance to sample one
   distinct map cell for every entity.
5. Replace each selected empty cell with an occupied immutable `MapCell` and
   store that same cell in the relevant location mapping.
6. Construct the complete connectivity graph.

RUs and users cannot share a cell, and no cell contains more than one entity.
The environment is structurally static after construction: it does not support
mobility or runtime addition and removal of entities. RU battery and status
remain mutable through the RU's existing public methods.

A fixed seed reproduces both placements and connectivity weights across
separately constructed environments with the same configuration. A `None` seed
allows nondeterministic construction.

## Owned State

`Environment` privately owns:

- the two-dimensional map;
- the RU list;
- the user list;
- an `RU`-to-`MapCell` location mapping;
- a `User`-to-`MapCell` location mapping; and
- the NetworkX connectivity graph.

The map occupancy and location mappings contain redundant placement
information for efficient access. Construction updates both representations
together, and the absence of mobility keeps them consistent afterward.

## Connectivity Graph

NetworkX is added as a runtime dependency through uv. The environment owns one
undirected `networkx.Graph`. Every RU and user is added as a node, including
isolated entities. RU nodes receive `bipartite=0`, and user nodes receive
`bipartite=1`. Only RU-to-user edges may exist; there are no RU-to-RU or
user-to-user edges.

For each RU-user pair, the environment calculates the distance between their
location cells. A pair has no edge when:

```text
distance >= ru_config.coverage_radius
```

For a pair inside the coverage radius, its edge receives a `weight` attribute
calculated as:

```text
closeness = 1 - distance / coverage_radius
random_factor = 1 - random()
weight = random_factor * closeness
```

Python's `random()` produces a value in `[0, 1)`, so `1 - random()` lies in
`(0, 1]`. Every stored edge therefore has a strictly positive weight no greater
than its distance-derived closeness. Using a positive random factor preserves
the semantic distinction between an edge and the `0.0` returned for no edge.
The weight distribution scales linearly downward as distance increases.

## Public Interface

`Environment` exposes:

```python
get_map() -> list[list[MapCell]]
get_rus() -> list[RU]
get_users() -> list[User]
get_ru_locations() -> dict[RU, MapCell]
get_user_locations() -> dict[User, MapCell]
get_connectivity_graph() -> nx.Graph
get_connection_weight(user: User, ru: RU) -> float
```

Collection getters return new list, row, or dictionary containers holding the
same entities and immutable cells. The graph getter returns a graph copy.
Changing a returned container or graph therefore cannot change the
environment's structural state, while RU objects remain shared so their
battery and status can be updated by controllers.

`get_connection_weight()` returns the edge's positive numeric `weight`, or
`0.0` when no edge exists. The method verifies RU and user ownership by object
identity before looking up the edge, so an equal-valued entity from another
environment is still treated as foreign and returns `0.0`.

## Testing

Tests mirror the new source boundaries and cover:

- `MapCell` coordinate validation, occupant validation, distance calculation,
  and immutability;
- complete removal of `Point` from supported imports;
- immutable nested configuration and all environment-specific validation;
- propagation of existing RU validation for invalid RU settings;
- row-major map dimensions and coordinate values;
- uniform RU creation and sequential RU and user IDs;
- collision-free placement and agreement between occupants and both location
  mappings;
- reproducible placements and weights for equal seeds;
- NetworkX node membership, bipartite attributes, isolated nodes, and
  undirected weighted edges;
- exclusion of pairs at or beyond the coverage radius;
- positive weights bounded by distance-derived closeness;
- zero weight lookup for missing edges and foreign entities; and
- protection of internal structural state from mutations to returned
  collections and graph copies.

The complete pytest suite, Ruff lint, Ruff formatting check, and Git whitespace
check must pass.

## Documentation and Dependency Changes

The README is updated to describe `MapCell`, environment configuration,
construction, placement, connectivity, and reproducible seeds. NetworkX is
added using `uv add networkx`, and both `pyproject.toml` and `uv.lock` are
committed.

## Scope Boundaries

This change does not add mobility, entity addition or removal after
construction, environment reset, graph recalculation, configuration-file
loading, heterogeneous RU settings, user behavior, simulation-controller
orchestration, or connectivity metrics.
