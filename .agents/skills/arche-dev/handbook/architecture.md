# Architecture

## Philosophy

Arche follows a **microkernel architecture**: the core layer handles only assembly and orchestration, never business logic. All features live in plugins. This ensures the core remains stable while features can be added, removed, or modified independently.

## Project Layout

```
Project Root/
├── backend/               # Python backend (FastAPI)
│   ├── core/              # Kernel — never changes
│   │   ├── __init__.py    # create_app() — boot sequence
│   │   ├── database.py    # DB init (SQLite/PostgreSQL)
│   │   ├── di.py          # ServiceContainer (DI)
│   │   └── plugin.py      # Plugin loader & activator
│   ├── plugins/           # All features, auto-discovered
│   │   ├── blog/          # Example plugin
│   │   ├── auth/
│   │   └── ...
│   ├── main.py            # FastAPI app entry point
│   └── tests/
├── frontend/              # Vue 3 + TypeScript + Vite
│   └── src/
│       ├── components/    # ui/, blog/, admin/, user/
│       ├── layouts/       # BaseLayout, BlogShell, etc.
│       ├── router/        # Role-based routing
│       └── services/      # API client
├── scripts/               # Custom lint, tooling
├── docker-compose.yml     # Prod deployment
└── pyproject.toml         # Backend deps
```

## Boot Sequence

`backend/core/__init__.py` `create_app()` executes in this exact order:

1. **Logging** — configure structured logging
2. **Database init** — create async engine, session factory
3. **ServiceContainer** — bootstrap DI container
4. **Plugin activation** — scan `backend/plugins/`, sort by DAG (respecting `requires`/`optional`), activate each plugin
5. **Plugin service registration** — each plugin registers its services into the container
6. **Middleware** — attach global middleware (CORS, session tracking, etc.)
7. **Startup hooks** — Alembic auto-migration, schema validation, config seeding
8. **Static files mount** — if `frontend/dist/` exists, mount as static file server at `/`

## Plugin Discovery

Plugins are auto-discovered from `backend/plugins/`. No manual registration is needed. Each plugin directory must contain:

- `__init__.py` — plugin class definition + self-registration via `@plugin_registry.register`
- `routes.py` — FastAPI route definitions (optional)
- `services.py` — business logic (optional)
- `models.py` — SQLAlchemy models (optional)

### DAG-based Activation

Plugins declare dependencies via `requires` (hard dependency) and `optional` (soft dependency):

```python
class BlogPlugin(BasePlugin):
    name = "blog"
    requires = ["auth"]       # auth must be active first
    optional = ["oss"]        # oss enhances blog but blog works without it
```

The activator sorts plugins topologically. If a `requires` dependency is missing, the plugin is deactivated with a logged warning. Missing `optional` deps are silently skipped.

## Core vs Plugin Boundary

| Aspect | Core (`backend/core/`) | Plugin (`backend/plugins/*/`) |
|--------|----------------------|------------------------------|
| Responsibility | Assembly, orchestration, DI | Business logic, features |
| Changes | Almost never | Frequently |
| Dependencies | FastAPI, SQLAlchemy, Pydantic | Any, but scoped to plugin |
| Testing | Core integration tests | Plugin-specific tests |

## Key Files Reference

| File | Purpose |
|------|---------|
| [backend/core/__init__.py](file:///d:/Project/Arche/backend/core/__init__.py) | `create_app()` — boot sequence |
| [backend/core/database.py](file:///d:/Project/Arche/backend/core/database.py) | DB engine, session management |
| [backend/core/di.py](file:///d:/Project/Arche/backend/core/di.py) | ServiceContainer — DI container |
| [backend/core/plugin.py](file:///d:/Project/Arche/backend/core/plugin.py) | Plugin loader, DAG sorter, activator |
| [backend/main.py](file:///d:/Project/Arche/backend/main.py) | FastAPI app entry |
