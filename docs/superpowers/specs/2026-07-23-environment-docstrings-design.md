# Environment Method Docstrings Design

## Goal

Add concise implementation-focused docstrings to
`Environment._place_entities()` and `Environment._create_connectivity_graph()`
so future developers can understand each algorithm without reading every line.

## Docstring Content

The `_place_entities()` docstring will summarize that the method:

- flattens the row-major map;
- uses the environment's random generator to sample one distinct cell per
  entity;
- replaces each selected immutable cell with an occupied cell; and
- stores that same cell in the appropriate entity-location mapping.

The `_create_connectivity_graph()` docstring will summarize that the method:

- adds every RU and user as nodes in a bipartite graph;
- evaluates every RU-user pair against the configured coverage radius; and
- weights qualifying edges using distance-derived closeness and the
  environment's random generator.

## Style and Scope

Use compact multi-line Python docstrings immediately below each function
signature. Describe implementation mechanics rather than restating only the
function name. Do not document private local variables individually, change
runtime behavior, alter public interfaces, or add docstrings to unrelated
methods.

## Validation

Run the environment tests, Ruff lint, Ruff formatting check, and Git whitespace
check. Confirm that the only source change beyond the existing variable rename
is the two approved docstrings.
