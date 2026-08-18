# Multi-Seed Simulation Runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run every supported controller policy with ten reproducible seeds via `make run-all`, storing each run's metric JSON files in a unique output directory.

**Architecture:** The configuration hierarchy becomes the source of truth for batch runs: each numbered iteration directory owns one copy of all three policy configurations and one shared seed.  The Makefile enumerates that fixed hierarchy and recursively invokes its existing `run` target, which continues to own the Python command and per-run metric-output path.

**Tech Stack:** YAML configuration files, GNU Make, Python 3.12, pytest, uv, Ruff.

**Spec:** `docs/superpowers/specs/2026-08-18-multi-seed-simulation-runs-design.md`

## Global Constraints

- Create exactly ten configuration directories named `configs/iteration-01` through `configs/iteration-10`.
- Every iteration contains exactly `always_active.yaml`, `staggered_active.yaml`, and `threshold_staggered_active.yaml`.
- Use the same `environment.random_seed` for all policies in an iteration; set the seeds to the matching integers `1` through `10`.
- Retain `configs/default.yaml` for one-off runs and remove the three former flat policy configuration files.
- `make run-all` runs all thirty iteration-policy combinations in numeric iteration order and policy order: `always_active`, `staggered_active`, then `threshold_staggered_active`.
- Each batch run writes only to `outputs/iteration-XX/<policy>/`, using the existing metric JSON file names and schema.
- Stop on the first failed run; do not delete, aggregate, or modify output from completed runs.
- Preserve `make run` and its `CONFIG` and `METRICS_OUTPUT_PATH` overrides, do not change simulator behavior or add dependencies, and run all project commands through `uv`.

---

## File Structure

- Create: `configs/iteration-01/` through `configs/iteration-10/`: three complete policy YAML configurations per iteration.
- Delete: `configs/always_active.yaml`, `configs/staggered_active.yaml`, `configs/threshold_staggered_active.yaml`: superseded flat policy files.
- Create: `tests/test_batch_configurations.py`: integration coverage for the configuration hierarchy, policy selection, seeds, and loader validity.
- Modify: `Makefile`: centralize batch iteration/policy names and implement `run-all` by calling `$(MAKE) run` with explicit config and output paths.
- Create: `tests/test_makefile.py`: use `make --dry-run run-all` to verify the thirty command pairs and their order without executing simulations.
- Modify: `README.md`: document the batch hierarchy, shared-seed rationale, batch command, and output layout.

### Task 1: Add the Iteration Configuration Hierarchy

**Files:**
- Create: `tests/test_batch_configurations.py`
- Create: `configs/iteration-01/always_active.yaml`
- Create: `configs/iteration-01/staggered_active.yaml`
- Create: `configs/iteration-01/threshold_staggered_active.yaml`
- Create: equivalent three-file sets for `iteration-02` through `iteration-10`
- Delete: `configs/always_active.yaml`
- Delete: `configs/staggered_active.yaml`
- Delete: `configs/threshold_staggered_active.yaml`

**Interfaces:**
- Consumes: the public `load_config(path: Path) -> ApplicationConfig` loader and `ControllerKind` enum.
- Produces: the authoritative `configs/iteration-XX/<policy>.yaml` batch input paths consumed by Task 2's Makefile loop.

- [ ] **Step 1: Write the failing configuration-hierarchy tests**

Create `tests/test_batch_configurations.py`.  Resolve `PROJECT_ROOT` with
`Path(__file__).resolve().parents[1]`.  Define these constants and expected
controller mapping:

```python
ITERATIONS = tuple(f"iteration-{number:02d}" for number in range(1, 11))
POLICIES = (
    "always_active",
    "staggered_active",
    "threshold_staggered_active",
)
EXPECTED_KINDS = {
    "always_active": ControllerKind.ALWAYS_ACTIVE,
    "staggered_active": ControllerKind.STAGGERED_ACTIVE,
    "threshold_staggered_active": ControllerKind.THRESHOLD_STAGGERED_ACTIVE,
}
```

Add `test_iteration_configurations_are_complete_and_loader_valid()`.  For
each iteration, assert that the names of its immediate `*.yaml` files equal
the `POLICIES` set; load every expected file with `load_config`; assert its
controller kind equals `EXPECTED_KINDS[policy]`; collect all three random
seeds and assert they equal `{iteration_number}`.  At the end, assert the
flattened seeds equal `set(range(1, 11))`.  Add
`test_flat_policy_configurations_are_absent()` asserting that the three old
`configs/<policy>.yaml` paths do not exist while `configs/default.yaml` does.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_batch_configurations.py -v`

Expected: FAIL because `configs/iteration-01` does not yet exist and the
three old flat files still exist.

- [ ] **Step 3: Create the thirty YAML files and remove the old flat files**

Use the three current flat policy YAML files as the full templates.  Create
the three policy files under each `configs/iteration-XX/` directory, with
identical content except for `environment.random_seed`.  Set every policy in
`iteration-01` to `1`, every policy in `iteration-02` to `2`, continuing
through seed `10` in `iteration-10`.  Preserve the policy-specific controller
blocks exactly: only the threshold policy contains
`threshold_percentage: 50.0`.  Then delete the three flat policy files.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_batch_configurations.py -v`

Expected: PASS.  This proves all thirty YAML documents load, each iteration
has all policies, policies share their iteration seed, seeds are distinct
across iterations, and no stale flat policy configs remain.

- [ ] **Step 5: Commit the configuration hierarchy**

```bash
git add configs tests/test_batch_configurations.py
git commit -m "feat: add multi-seed policy configurations"
```

### Task 2: Make `run-all` Execute the Thirty Runs

**Files:**
- Create: `tests/test_makefile.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: Task 1's `configs/iteration-XX/<policy>.yaml` paths and the
  existing `run` target's `CONFIG` and `METRICS_OUTPUT_PATH` parameters.
- Produces: `make run-all`, which emits exactly thirty `uv run python main.py`
  invocations when dry-run and invokes the existing `run` target when run.

- [ ] **Step 1: Write the failing Makefile dry-run test**

Create `tests/test_makefile.py`.  Use `subprocess.run` with
`["make", "--dry-run", "run-all"]`, `cwd=PROJECT_ROOT`, `check=True`,
`text=True`, and `capture_output=True`.  Filter `completed.stdout.splitlines()`
to lines beginning with `"uv run python main.py "`.  Build expected command
lines with nested iteration and policy loops:

```python
expected_commands = [
    "uv run python main.py "
    f"--configs configs/iteration-{number:02d}/{policy}.yaml "
    f"--metrics-output-path outputs/iteration-{number:02d}/{policy}"
    for number in range(1, 11)
    for policy in (
        "always_active",
        "staggered_active",
        "threshold_staggered_active",
    )
]
```

Assert the filtered lines equal `expected_commands`.  This protects both the
complete thirty-run expansion and the required ordering without running the
simulator or producing metrics files.

- [ ] **Step 2: Run the new test to verify it fails**

Run: `uv run pytest tests/test_makefile.py -v`

Expected: FAIL because the current `run-all` references only the three former
flat config paths instead of all thirty expected commands.

- [ ] **Step 3: Centralize batch names and update `run-all`**

Add Make variables exactly as follows near the existing `CONFIG` and
`METRICS_OUTPUT_PATH` defaults:

```make
ITERATIONS := $(shell seq -w 1 10)
POLICIES := always_active staggered_active threshold_staggered_active
```

Replace the three explicit `run-all` recipe lines with this one shell loop:

```make
\t@set -e; for iteration in $(ITERATIONS); do \\
\t\tfor policy in $(POLICIES); do \\
\t\t\t$(MAKE) run CONFIG=configs/iteration-$$iteration/$$policy.yaml \\
\t\t\t\tMETRICS_OUTPUT_PATH=outputs/iteration-$$iteration/$$policy; \\
\t\tdone; \\
\tdone
```

Keep the existing `run` recipe unchanged.  Update the `help` target's
`run-all` description to say it runs all 10 seeds × 3 policy scenarios and
writes outputs beneath `outputs/`.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `uv run pytest tests/test_makefile.py -v`

Expected: PASS with exactly thirty expected dry-run Python command lines in
iteration-major, policy-minor order.

- [ ] **Step 5: Commit the batch command**

```bash
git add Makefile tests/test_makefile.py
git commit -m "feat: run every policy for ten seeds"
```

### Task 3: Document Batch Execution

**Files:**
- Modify: `README.md`
- Test: `tests/test_batch_configurations.py`
- Test: `tests/test_makefile.py`

**Interfaces:**
- Consumes: the validated configuration hierarchy from Task 1 and the
  `make run-all` contract from Task 2.
- Produces: user-facing instructions that map the batch command to its
  configuration and output paths.

- [ ] **Step 1: Write the failing documentation assertions**

Extend `tests/test_batch_configurations.py` with
`test_readme_documents_batch_runs()`.  Read `PROJECT_ROOT / "README.md"` and
assert it contains each of these exact strings:

```python
"make run-all"
"configs/iteration-01/always_active.yaml"
"outputs/iteration-01/always_active/"
"same random seed"
```

The test keeps the published command, representative config path, output
path, and shared-seed comparison guarantee from drifting apart.

- [ ] **Step 2: Run the documentation test to verify it fails**

Run: `uv run pytest tests/test_batch_configurations.py::test_readme_documents_batch_runs -v`

Expected: FAIL because the current README does not yet document the batch
configuration hierarchy or `make run-all`.

- [ ] **Step 3: Add concise batch-run README documentation**

Add a `## Batch Runs` section after the existing Simulation section.  State
that there are ten directories from `configs/iteration-01/` to
`configs/iteration-10/`, that each contains the three named policy files,
and that all policies in one directory use the same random seed to support a
fair comparison.  Show this command:

```bash
make run-all
```

Explain it runs thirty simulations.  Show the representative input and
output paths `configs/iteration-01/always_active.yaml` and
`outputs/iteration-01/always_active/`, then state that each output leaf holds
the configured metric JSON files.  Keep the one-off invocation documentation
unchanged.

- [ ] **Step 4: Run documentation and formatting checks**

Run: `uv run pytest tests/test_batch_configurations.py tests/test_makefile.py -v`

Expected: PASS.  Then run: `uv run ruff format --check README.md tests/test_batch_configurations.py tests/test_makefile.py`

Expected: PASS with no formatting changes required.

- [ ] **Step 5: Commit the README update**

```bash
git add README.md tests/test_batch_configurations.py
git commit -m "docs: explain multi-seed batch runs"
```

### Task 4: Verify the Completed Batch Feature

**Files:**
- Verify: `configs/iteration-01/` through `configs/iteration-10/`
- Verify: `Makefile`
- Verify: `README.md`
- Verify: `tests/test_batch_configurations.py`
- Verify: `tests/test_makefile.py`

**Interfaces:**
- Consumes: the completed configuration hierarchy, Makefile command, and
  documentation from Tasks 1-3.
- Produces: final repository-wide verification evidence for the feature.

- [ ] **Step 1: Run all tests**

Run: `uv run pytest`

Expected: PASS with all existing and new tests green.

- [ ] **Step 2: Run static quality checks**

Run: `uv run ruff check .`

Expected: PASS with no lint findings.

Run: `uv run ruff format --check .`

Expected: PASS with no formatting changes required.

- [ ] **Step 3: Inspect the final batch expansion and working tree**

Run: `make --dry-run run-all`

Expected: the output includes exactly thirty `uv run python main.py` lines,
with no command using a removed flat policy configuration path.

Run: `git status --short`

Expected: no uncommitted tracked changes; the project-local worktree metadata
is ignored.

- [ ] **Step 4: Commit any verification-only updates if necessary**

If verification exposes no needed source changes, make no commit.  If a
verification correction is required, first add a focused failing regression
test, confirm its expected failure, make the smallest correction, rerun the
covering test and the full verification set, then commit only that correction
with a `test:` or `fix:` subject that describes it.

## Implementation Amendment (2026-08-18)

The user requested that this project contain no automated tests for the
Makefile or README. Consequently, `tests/test_makefile.py` and the
README-content assertion originally added to `tests/test_batch_configurations.py`
are removed. The remaining configuration-hierarchy tests continue to verify
the YAML inputs and their seeds; `make run-all` and the README are checked
manually when changed.
