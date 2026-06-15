# Plugin Development Guide

## Directory Structure

Every plugin lives under `backend/plugins/<plugin-name>/` with this standard structure:

```
backend/plugins/<plugin-name>/
├── __init__.py         # Plugin class + self-registration (REQUIRED)
├── routes.py           # FastAPI router (optional)
├── services.py         # Business logic (optional)
├── models.py           # SQLAlchemy models (optional)
└── tests/              # Plugin-specific tests (optional)
    └── ...
```

## Plugin Class Template

```python
# backend/plugins/<plugin-name>/__init__.py

from core.plugin import BasePlugin, plugin_registry

class MyPlugin(BasePlugin):
    name = "my-plugin"                # kebab-case unique identifier
    requires = ["auth"]               # hard dependencies (optional)
    optional = ["oss"]                # soft dependencies (optional)

    def on_activate(self, container):
        """Called during boot sequence after DAG sort.
        Register services, attach middleware, etc."""
        container.register("my_service", MyService)
        return True                    # False = activation failed

    def on_deactivate(self, container):
        """Called during shutdown. Clean up resources."""
        pass

# Self-registration — this line is REQUIRED
plugin_registry.register(MyPlugin)
```

## Plugin Components

### routes.py

Define FastAPI routers. Each plugin creates its own `APIRouter` with a prefix:

```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/my-plugin", tags=["my-plugin"])

@router.get("/items")
async def list_items():
    return {"items": []}
```

Register the router in `on_activate`:

```python
def on_activate(self, container):
    from .routes import router
    container.get("app").include_router(router)
    return True
```

### services.py

Business logic classes. Use constructor injection:

```python
class MyService:
    def __init__(self, db_session, auth_service=None):
        self.db = db_session
        self.auth = auth_service
```

### models.py

SQLAlchemy models. Each model inherits from the core `Base`:

```python
from core.database import Base
from sqlalchemy import Column, Integer, String

class MyItem(Base):
    __tablename__ = "my_items"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
```

## Activation Lifecycle

1. `on_activate(container)` — called at boot. Return `False` to signal failure.
2. Plugin is active for the entire application lifetime.
3. `on_deactivate(container)` — called at shutdown.

If `on_activate` returns `False`, the plugin is marked as failed and its routes/services are not available.

## Encapsulation Rules

- **Never import from another plugin's internal modules** — use `ServiceContainer` to access cross-plugin services.
- **Never modify core code** — if you need a new core capability, open a discussion.
- **Keep plugin tests in `backend/tests/`** under the standard test structure, or in `backend/plugins/<name>/tests/`.
