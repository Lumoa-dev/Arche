# Testing Strategy

## Backend (pytest)

### Philosophy

**All tests are real integration tests.** No mocks, no simulated databases, no MagicMock.
Every test starts a real FastAPI application with all plugins activated, uses a real
SQLite file-based database (with Alembic migrations running at startup), and sends
real HTTP requests through the complete ASGI stack (routing → middleware → services → DB).

### Running Tests

```bash
uv run pytest                                          # All tests (103+, coverage gate: 0%)
uv run pytest --no-cov -ra --tb=short                  # Quick run, no coverage
uv run pytest backend/tests/core/ -v                   # Core tests only
uv run pytest backend/tests/plugins/auth/ -v           # Auth plugin tests
uv run pytest backend/tests/ -k "blog" -v              # Keyword filter
uv run pytest backend/tests/core/test_app.py -v        # Single file
uv run pytest --ignore=backend/tests/plugins/request_log  # Skip known-failing plugin
```

### Test Structure

```
backend/tests/
├── conftest.py                # Global fixtures (app, async_client, auth_headers, admin_headers, db_session)
├── .gitignore                 # Ignores test DB files
├── core/                      # Core layer tests
│   ├── test_app.py            # App creation, boot sequence, health check, CORS, 404
│   ├── test_db.py             # DB init, table creation, config seeding
│   ├── test_config.py         # ConfigManager (env vars, defaults, cache, reload)
│   ├── test_container.py      # ServiceContainer (register, resolve, cycle detection)
│   ├── test_middleware.py     # Error handlers, security headers, get_real_ip()
│   └── test_migrations.py     # Alembic migration files, table existence
├── plugins/                   # Plugin-specific tests
│   ├── conftest.py            # plugin_app / plugin_client fixture factories
│   ├── auth/test_auth.py      # Register, login, logout, refresh, middleware, user mgmt
│   ├── blog/test_blog.py      # Posts CRUD, comments, tags
│   ├── oss/test_oss.py        # Upload, download, quota, type validation
│   ├── ip_ban/test_ip_ban.py  # Ban list, logs, rules, stats (admin)
│   ├── request_log/test_request_log.py  # Query logs, top IPs, trends (admin)
│   └── config_mgmt/test_config_mgmt.py  # Config list, admin auth
```

### Key Fixtures

All fixtures are in `backend/tests/conftest.py`:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `app` | session | Real FastAPI app, all plugins active, SQLite file-based DB |
| `async_client` | function | `httpx.AsyncClient` via ASGI transport (real HTTP, no TCP) |
| `client` | function | Sync `TestClient` (triggers lifespan events) |
| `auth_headers` | function | Register user → return `{"Authorization": "Bearer <jwt>"}` (level=?) |
| `admin_headers` | function | Register user + DB-update level=0 → return admin JWT |
| `db_session` | function | Real async DB session from app's session factory |

### How Tests Work

1. **`app()` fixture** (session-scoped):
   - Resets plugin registry, discovers all 14 plugins
   - Calls `create_app()` with env vars `DATABASE_URL=sqlite+aiosqlite:///./test_arche.db`, `SECRET_KEY=test-secret-key-for-pytest`
   - Creates a `TestClient(app)` to trigger lifespan startup events (Alembic migration → ensure_tables → seed config → plugin on_startup)

2. **`async_client()` fixture** (function-scoped):
   - Creates `httpx.AsyncClient(transport=ASGITransport(app=app))`
   - Sends real HTTP requests through the full ASGI stack

3. **`auth_headers()` / `admin_headers()`**:
   - Actually call `POST /api/auth/register` + `POST /api/auth/login` on the real backend
   - `admin_headers` also updates the user's level to 0 in the database

### Adding a New Plugin Test

```python
"""MyPlugin plugin tests."""

import pytest

PREFIX = "/api/my-plugin"

class TestMyPlugin:
    @pytest.mark.asyncio
    async def test_list(self, async_client, auth_headers):
        resp = await async_client.get(PREFIX, headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_only(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/admin", headers=admin_headers)
        assert resp.status_code == 200
```

### Database in Tests

- **Dev/CI (SQLite)**: File-based `test_arche.db` in the tests directory
- **CI (PostgreSQL)**: Set `ARCHE_TEST_DB_URL=postgresql+asyncpg://...` env var
- Alembic migration runs at startup to create tables via the migration chain
- `ensure_tables()` catches any tables not in the migration chain (idempotent)

### Known Issues

- `request_log` plugin: routes return 500 because the `request_logs` table is not
  created by the initial Alembic migration. Fix: add migration or ensure `ensure_tables()`
  runs before the middleware intercepts requests.

### Coverage Gate

Currently set to **0%** (new codebase). Raise incrementally as tests mature.

### Test Markers

| Marker | Description |
|--------|-------------|
| (none) | Default — real integration test |
| `real` | Requires external services (GitHub API, etc.) — CI only |
| `slow` | Slow test requiring network |
