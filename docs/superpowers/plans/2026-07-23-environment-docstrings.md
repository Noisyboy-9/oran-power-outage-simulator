# Environment Method Docstrings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document how entity placement and connectivity-graph construction work without changing runtime behavior.

**Architecture:** Add compact multi-line Python docstrings directly below the two private method signatures. Keep the existing `flattened_map` rename and make no other source changes.

**Tech Stack:** Python 3.12, pytest, Ruff, Git

## Global Constraints

- Describe implementation mechanics rather than merely restating method names.
- Keep both docstrings concise and summarized.
- Do not change behavior, public interfaces, or unrelated methods.
- Preserve the existing `available_cells` to `flattened_map` rename.

---

### Task 1: Add and verify the environment method docstrings

**Files:**

- Modify: `src/simulator/environment/environment.py`
- Test: `tests/environment/`
- Reference: `docs/superpowers/specs/2026-07-23-environment-docstrings-design.md`

**Interfaces:**

- Consumes: `Environment._place_entities()` and
  `Environment._create_connectivity_graph()` as currently implemented.
- Produces: concise implementation documentation with no runtime interface or
  behavior change.

- [x] **Step 1: Add both docstrings**

Add this docstring directly below `_place_entities()`:

```python
"""Place entities using the environment's random number generator.

The row-major map is flattened for sampling. Each selected immutable cell
is replaced with an occupied copy and stored in the matching location map.
"""
```

Add this docstring directly below `_create_connectivity_graph()`:

```python
"""Build the weighted bipartite graph from current entity locations.

Every RU and user becomes a node. Pairs inside the coverage radius receive
an edge weighted by distance-derived closeness and the environment's random
number generator.
"""
```

- [x] **Step 2: Run focused and project quality checks**

Run:

```bash
uv run pytest tests/environment -q
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Expected: 51 environment tests pass, Ruff reports no lint or formatting
problems, and Git reports no whitespace errors.

- [x] **Step 3: Review and commit the source and plan**

Run:

```bash
git diff -- src/simulator/environment/environment.py
git status --short
git add src/simulator/environment/environment.py
git add docs/superpowers/plans/2026-07-23-environment-docstrings.md
git diff --cached --check
git commit -m "docs: explain environment construction helpers"
```

Expected: the commit contains the existing local variable rename, the two
docstrings, and this plan; no unrelated files are included.
