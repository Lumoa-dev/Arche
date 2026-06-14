# Backend Conventions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.110+ |
| ORM | SQLAlchemy 2.x (async) |
| DB Driver | aiosqlite (dev), asyncpg (production) |
| Validation | Pydantic v2 |
| DI | Custom ServiceContainer in `core/di.py` |
| Migration | Alembic (auto-run at startup) |
| Lint | ruff + custom rules (`scripts/lint_rules.py`) |
| Auth | JWT (via `auth` plugin) |

## Coding Constraints

### No Lambda

Python `lambda` is forbidden by custom lint. Use named functions instead:

```python
# BAD
sorted(items, key=lambda x: x.name)

# GOOD
def _sort_key(x):
    return x.name
sorted(items, key=_sort_key)
```

**Whitelisted exceptions** (these 3 patterns only):
1. SQLAlchemy column defaults: `Column(DateTime, default=lambda: datetime.utcnow())`
2. `iter()` sentinel: `iter(fn, lambda: sentinel)`
3. DI container factories: `container.register("x", lambda: X())`

### No Nested Comprehensions

Max 1 level of nesting:

```python
# BAD — nested comprehension
result = [y for x in items if x.active for y in x.children if y.valid]

# GOOD — flatten with intermediate variables
active_items = [x for x in items if x.active]
result = [y for x in active_items for y in x.children if y.valid]
```

### Naming Conventions

- Python: `snake_case` for functions, variables, modules
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- FastAPI endpoints: plural nouns, `kebab-case` paths: `/api/posts/{post-id}`
- Plugin names: `kebab-case` (e.g., `blog`, `config_mgmt`, `github_proxy`)

## Database

### Connection

```python
# SQLite (dev)
DATABASE_URL = "sqlite+aiosqlite:///./arche.db"

# PostgreSQL (prod)
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db"
```

### Session Management

Use async sessions. For tests with in-memory SQLite, use `StaticPool` to share the connection across sessions:

```python
from sqlalchemy.pool import StaticPool

engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
```

### Config Layering (priority order)

1. Database config (runtime dynamic, with TTL cache)
2. Environment variables
3. `.env` file

The `config_mgmt` plugin handles runtime dynamic configuration with TTL-based cache invalidation.

## Alembic

Migrations run **automatically at startup** via the startup hook. No manual CLI step is needed. The migration logic is in `core/__init__.py` and checks for pending migrations before applying them.

## Router Convention

```python
router = APIRouter(prefix="/api/<plugin-name>", tags=["<plugin-name>"])

# CRUD endpoints
@router.get("/items")
@router.get("/items/{item-id}")
@router.post("/items")
@router.put("/items/{item-id}")
@router.delete("/items/{item-id}")
```

## Error Handling

Use HTTPException with structured error responses:

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="Item not found")
```

For business logic errors, define custom exception classes in the plugin's `services.py` and catch them in the route handler.
