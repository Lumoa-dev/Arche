---
name: "arche-dev"
description: "Arche project development handbook. Covers architecture, plugin development, frontend/backend conventions, testing, CI/CD, issue management, project standards, and experience distillation. Triggered when working with Arche codebase or project conventions. IMPORTANT: proactively read experiences.md and standards.md before starting tasks, and distill new lessons into experiences.md after completing tasks."
---

# Arche Development Skill

You are an AI assistant specialized in the Arche project. This skill provides the complete knowledge base for developing, maintaining, and extending the Arche platform.

## Pre-read (Mandatory)

Before starting any task, you MUST:

1. **Read [experiences.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/experiences.md)** — check for relevant lessons and pitfalls
2. **Read [standards.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/standards.md)** — review project conventions (labels, templates, format policies)
3. **Read the relevant handbook page(s)** from the index below based on the task at hand
4. After completing the task, **distill any new lessons** into `experiences.md`

## Core Identity

Arche is a **microkernel + plugins** personal platform:
- `backend/core/` — the "never-changing" kernel. Boot sequence: Logging → DB init → ServiceContainer → Plugin activation → Middleware → Startup hooks
- `backend/plugins/` — all features are self-contained plugins, auto-discovered at startup
- `frontend/` — Vue 3 + TypeScript + Vite, with role-based code splitting (blog/platform/admin)

## Immutable Rules

These rules MUST be followed in ALL code generation for Arche:

1. **No lambda** — use named functions instead. Exceptions (3 whitelisted patterns): SQLAlchemy column defaults, `iter()` sentinel, DI container factories.
2. **No nested comprehensions** — max 1 level of nesting. Use named intermediate variables instead.
3. **All code comments and documentation in Chinese** — this is a project-wide convention.
4. **Plugin encapsulation** — every plugin is self-contained with its own `__init__.py`, `routes.py`, `services.py`, `models.py`. Never modify core for a plugin feature.
5. **No frontend vanilla JS** — all frontend code MUST use TypeScript.

## Quick Reference

```bash
# Backend
uv sync                          # install deps
uv run uvicorn backend.main:app --reload   # dev server (port 8000)
uv run ruff check backend/       # lint
uv run ruff format backend/      # format
uv run pytest                    # tests

# Frontend
cd frontend && npm install       # install deps
cd frontend && npm run dev       # dev server (port 5173)
cd frontend && npm run lint      # lint
cd frontend && npm run type-check # type check
cd frontend && npm run test:run  # tests (single run)
```

## Handbook Index

All detailed documentation is in the `handbook/` subdirectory:

| File | When to Read |
|------|-------------|
| [architecture.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/architecture.md) | Understand project architecture, boot sequence, core vs plugin boundary |
| [plugin-dev.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/plugin-dev.md) | Create a new plugin or modify an existing one |
| [backend.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/backend.md) | Write backend code — models, routes, services, DB, config |
| [frontend.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/frontend.md) | Write frontend code — components, API calls, routing, design system |
| [testing.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/testing.md) | Write or run tests — pytest/vitest patterns, fixtures, coverage |
| [cicd.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/cicd.md) | Understand CI/CD pipeline, build, deploy, versioning |
| [experiences.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/experiences.md) | **Experience log** — non-obvious pitfalls and reusable insights (English, compact format). MUST read before any task |
| [standards.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/standards.md) | **Project standards** — label system, Epic format, template policies. MUST read before any task |
| [issue-management.md](file:///d:/Project/Arche/.trae/skills/arche-dev/handbook/issue-management.md) | Issue labels, templates, Epic + Sub-issue structure, creation workflow, management flow |
