# Agent Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add balanced, repository-wide instructions that let AI coding agents work safely and consistently on the simulator.

**Architecture:** A single root-level `AGENTS.md` applies to the complete repository. It records current project facts, architectural boundaries, exact development commands, mandatory user rules, and completion criteria without defining speculative APIs.

**Tech Stack:** Markdown, Python 3.12, uv, pytest, Ruff, Git

## Global Constraints

- The guidance applies to the entire simulator repository.
- The filename is the conventional uppercase `AGENTS.md`.
- The guide must remain concise and project-specific.
- It must not invent future class interfaces, algorithms, or metric formulas.
- The user's three rules must appear verbatim in a clearly labeled `Rules` section.

---

### Task 1: Add repository-wide agent guidance

**Files:**

- Create: `AGENTS.md`
- Reference: `README.md`
- Reference: `pyproject.toml`
- Reference: `docs/superpowers/specs/2026-07-13-agent-guidance-design.md`

**Interfaces:**

- Consumes: the current repository layout, uv commands, Ruff configuration, pytest configuration, and approved agent-guidance design.
- Produces: repository-wide instructions automatically discoverable by AI coding agents.

- [x] **Step 1: Create `AGENTS.md` with the approved content**

Create `AGENTS.md` with exactly this content:

```markdown
# AGENTS.md

## Project Overview

This repository contains a custom dependable-networking simulator. It uses Python 3.12, a `src` package layout, and uv for environment and dependency management.

The project is currently a scaffold. Do not invent simulation behavior, public APIs, timing semantics, or metric definitions unless the task explicitly requires those decisions.

These instructions apply to the entire repository.

## Rules

These rules are mandatory:

- Make sure you think before writing code
- Make sure you implement the easiest solution possible, don't make the code over-complicated
- Make sure you write easy to maintain and understand code

## Repository Layout

- `src/simulator/domain/`: core simulation objects such as `Point`, `RU`, and `User`
- `src/simulator/controllers/`: the RU-controller abstraction and activation policies
- `src/simulator/metrics/`: the metric-collector abstraction and individual collectors
- `src/simulator/environment.py`: ownership of entities and complete simulation state
- `src/simulator/simulation_controller.py`: time-step and component orchestration
- `tests/`: pytest tests organized to mirror the source package
- `docs/superpowers/`: approved design specifications and implementation plans

## Architecture Boundaries

- Keep domain objects independent of orchestration and infrastructure concerns.
- Controllers may depend on domain objects but should not own the complete environment.
- Metric collectors observe simulation state; they do not control simulation behavior.
- The environment owns entities and mutable simulation state.
- The simulation controller coordinates steps, controllers, environment updates, and metric collection.
- Avoid circular dependencies and hidden global state.
- Keep each module focused on one clear responsibility.
- Do not introduce abstractions, factories, configuration layers, or dependencies until a concrete requirement justifies them.

## Development Workflow

1. Read the relevant source, tests, documentation, and current Git diff before editing.
2. Confirm the requested behavior and identify the smallest coherent change.
3. Add or update tests when behavior changes.
4. Implement the simplest solution that satisfies the requirement.
5. Run focused checks during development and the full verification set before completion.
6. Summarize what changed, what was verified, and any remaining limitations.

Use uv for dependency changes:

```bash
uv add <package>
uv add --dev <development-package>
uv remove <package>
```

Commit the updated `uv.lock` whenever project dependencies change.

## Commands

Run commands from the repository root.

```bash
# Create or synchronize the development environment
uv sync --dev

# Run the test suite
uv run pytest

# Lint
uv run ruff check .

# Check formatting without modifying files
uv run ruff format --check .

# Apply formatting
uv run ruff format .
```

The test files are currently empty placeholders. The first behavior implementation must introduce corresponding tests; after that, `uv run pytest` must exit successfully before completion.

## Testing and Quality

- Mirror source boundaries under `tests/` and use descriptive `test_<behavior>` names.
- Test externally visible behavior rather than private implementation details.
- Keep tests deterministic; avoid real-time sleeps, uncontrolled randomness, network access, and shared mutable state.
- Add regression tests for bug fixes.
- Cover normal behavior, meaningful boundary cases, and failure behavior required by the task.
- Do not weaken or delete tests merely to make a change pass.
- Run Ruff lint and format checks before reporting completion.

## Code and Documentation Conventions

- Target Python 3.12 or newer, but do not raise the minimum version without approval.
- Use clear domain terminology and descriptive names.
- Add type hints to public interfaces and non-obvious internal boundaries.
- Prefer small functions, explicit data flow, and standard-library features.
- Avoid speculative extensibility and premature optimization.
- Write comments for reasoning or constraints, not to restate obvious code.
- Update `README.md`, this file, or relevant design documentation when setup, architecture, or commands change.

## Git Hygiene

- Preserve unrelated user changes and keep each change narrowly scoped.
- Inspect `git status` and the diff before committing or handing off work.
- Never commit `.venv`, caches, IDE state, build artifacts, or secrets.
- Do not use destructive Git commands unless the user explicitly requests them.
- Use focused commit messages that describe the completed change.

## Definition of Done

A change is complete only when:

- The requested behavior and approved design are satisfied.
- Relevant tests are added or updated and pass.
- `uv.lock` matches `pyproject.toml` when dependencies changed.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- Documentation reflects any changed setup, commands, or architecture.
- The final report states verification evidence and any unresolved limitations.
```

- [x] **Step 2: Verify required content and repository consistency**

Run:

```bash
test -f AGENTS.md
rg -F "Make sure you think before writing code" AGENTS.md
rg -F "Make sure you implement the easiest solution possible, don't make the code over-complicated" AGENTS.md
rg -F "Make sure you write easy to maintain and understand code" AGENTS.md
git diff --check
uv run ruff check .
uv run ruff format --check .
```

Expected: every command exits with status 0; each requested rule is printed once; Ruff reports no violations and no files requiring formatting.

- [x] **Step 3: Review and commit the documentation change**

Run:

```bash
git status --short
git diff -- AGENTS.md docs/superpowers/plans/2026-07-13-agent-guidance.md
git add AGENTS.md docs/superpowers/plans/2026-07-13-agent-guidance.md
git diff --cached --check
git commit -m "docs: add agent development guidance"
```

Expected: only `AGENTS.md` and this implementation plan are committed, and Git reports the new commit on `main`.
