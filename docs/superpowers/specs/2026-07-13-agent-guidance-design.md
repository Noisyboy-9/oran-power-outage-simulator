# Agent Guidance Design

## Goal

Add a root-level `AGENTS.md` that gives AI coding agents enough project context to work safely and consistently without prescribing interfaces or abstractions that the scaffold has not yet defined.

## Audience and Scope

The file applies to the entire simulator repository. It targets AI coding agents working on implementation, tests, documentation, and maintenance. It documents current repository facts and decision-making expectations; it does not define future class APIs, simulation algorithms, or metric formulas.

## Content

The guide will contain these concise sections:

1. **Project Overview** — purpose, Python 3.12 baseline, uv workflow, and the current scaffold status.
2. **Repository Layout** — responsibilities of the domain, controllers, metrics, environment, simulation controller, and tests.
3. **Architecture Boundaries** — dependency direction and responsibility separation, while avoiding premature interfaces.
4. **Development Workflow** — inspect before editing, keep changes scoped, add dependencies through uv, and mirror source changes with tests.
5. **Commands** — exact setup, test, lint, format-check, and formatting commands.
6. **Testing and Quality** — pytest expectations, deterministic tests, behavior-focused test naming, and required verification before completion.
7. **Code and Documentation Conventions** — Python 3.12, type hints for public interfaces, focused modules, clear naming, and documentation updates when workflows change.
8. **Git Hygiene** — preserve unrelated work, avoid destructive commands, keep generated files out of commits, and use focused commits.
9. **Rules** — the user's three mandatory rules, reproduced verbatim:
   - Make sure you think before writing code
   - Make sure you implement the easiest solution possible, don't make the code over-complicated
   - Make sure you write easy to maintain and understand code
10. **Definition of Done** — requirements met, tests added or updated for behavior, uv lock consistency, test/lint/format verification, and concise change reporting.

## Design Principles

- Prefer repository-specific instructions over generic programming advice.
- Keep the file scannable and avoid duplicating full documentation from `README.md` or `pyproject.toml`.
- State commands exactly as they should be run from the repository root.
- Distinguish mandatory rules from recommendations.
- Avoid requirements that conflict with the current empty scaffold or force speculative design decisions.

## Validation

Review the completed `AGENTS.md` against this design, confirm all commands match `pyproject.toml`, verify the three requested rules appear verbatim, run Markdown whitespace checks through Git, and confirm no unrelated files are changed.
