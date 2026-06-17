# Testing Strategy

## Backend (pytest)

### Philosophy

Arche follows a **three-layer testing strategy**:

1. **Unit tests** (`tests/unit/`) — Pure logic, no ASGI stack, no database. Tests cache logic, rate limiters, URL parsing, etc.
2. **Integration tests** (`tests/core/`, `tests/plugins/`) — Real FastAPI app with real database, sends real HTTP via ASGI transport.
   - Plugin tests use an isolated app with only the target plugin + its dependencies
   - Core tests use a full app with all plugins active
3. **Edge/Security tests** (`tests/edge_cases/`) — Integration tests focused on boundary conditions and attack vectors, run against the full app.

**External HTTP calls are mocked** via `pytest-httpx`. No test should depend on an external network service.

### Environment Auto-Detection

Arche uses `backend/tests/test_env.py` as the testing foundation's "eyes". It automatically detects:

| Signal | Detection Method | What It Means |
|--------|-----------------|---------------|
| Docker | `/.dockerenv` or `/proc/1/cgroup` | Running in container — PostgreSQL + MinIO should be available |
| WSL | `WSL_DISTRO_NAME` env or `/proc/version` | Can bridge to Windows-hosted services |
| CI | `CI`, `GITHUB_ACTIONS` etc. env vars | Running in CI pipeline |
| PostgreSQL | Port 5432 reachable (or `ARCHE_TEST_DB_URL` set) | Use real PostgreSQL for tests |
| MinIO | Port 9000 reachable | Use real MinIO for OSS tests |

The detection output is printed at the start of every test run:

```
[TestEnv] Environment: Windows | Services available: none (using local fallbacks)
[TestEnv] Database: SQLite in-memory (per-test)
[TestEnv] Storage: local
```

**Override**: Set `ARCHE_TEST_DB_URL` environment variable to force PostgreSQL mode regardless of auto-detection.

### Running Tests

```bash
uv run pytest                                          # All tests (270+, coverage gate: 0%)
uv run pytest --no-cov -ra --tb=short                  # Quick run, no coverage
uv run pytest backend/tests/unit/ -v                   # Pure logic (fast, <1s)
uv run pytest backend/tests/core/ -v                   # Core tests only
uv run pytest backend/tests/plugins/auth/ -v           # Auth plugin tests
uv run pytest backend/tests/edge_cases/ -v             # Boundary + Security tests
uv run pytest backend/tests/ -k "blog" -v              # Keyword filter
uv run pytest backend/tests/core/test_app.py -v        # Single file
uv run pytest --ignore=backend/tests/plugins/request_log  # Skip known-failing plugin
ARCHE_TEST_DB_URL=postgresql+asyncpg://user:pass@host/db uv run pytest  # Force PostgreSQL
```

### Test Structure

```
backend/tests/
├── conftest.py                # Global fixtures + env auto-detection
├── .gitignore                 # Ignores test DB files
├── test_env.py                # Environment detection module (Docker/WSL/CI/service ports)
├── unit/                      # Pure logic unit tests (no ASGI, no DB)
│   ├── test_logic.py          # CacheEntry, rate limiter, URL parsing, etc.
│   └── test_test_env.py       # test_env detection logic tests
├── core/                      # Core layer integration tests
│   ├── test_app.py            # App creation, boot sequence, health check, CORS, 404
│   ├── test_db.py             # DB init, table creation, config seeding
│   ├── test_config.py         # ConfigManager (env vars, defaults, cache, reload)
│   ├── test_container.py      # ServiceContainer (register, resolve, cycle detection)
│   ├── test_middleware.py     # Error handlers, security headers, get_real_ip()
│   ├── test_migrations.py     # Alembic migration files, table existence
│   ├── test_rate_limiter.py   # Rate limiter logic
│   ├── test_settings.py       # AppSettings / PluginSettings
│   └── test_uid.py            # UUID / SID formatting
├── edge_cases/                # Boundary + Security tests
│   ├── test_boundary.py       # Empty input, long input, method not allowed, concurrency, unicode
│   └── test_security.py       # SQL injection, XSS, path traversal, JWT, mass assignment, rate limit
├── plugins/                   # Plugin-specific integration tests
│   ├── conftest.py            # plugin_app / plugin_client fixture factories
│   ├── auth/test_auth.py      # Register, login, logout, refresh, middleware, user mgmt
│   ├── blog/test_blog.py      # Posts CRUD, comments, tags
│   ├── oss/test_oss.py        # Upload, download, quota, type validation
│   ├── ip_ban/test_ip_ban.py  # Ban list, logs, rules, stats (admin)
│   ├── request_log/test_request_log.py  # Query logs, top IPs, trends (admin)
│   ├── config_mgmt/test_config_mgmt.py  # Config list, admin auth
│   ├── crawler/test_crawler.py          # Seeds, blacklist, records, start/stop (admin)
│   ├── github_proxy/test_github_proxy.py  # Health, cache clear, raw file proxy (mocked)
│   ├── asset_mgmt/test_asset_mgmt.py    # Asset list, search, stats (admin)
│   ├── cloud_integration/test_cloud_integration.py  # Jobs, datasets, repos (admin)
│   ├── deploy_webhook/test_deploy_webhook.py  # Token validation, auth
│   ├── search/test_search.py            # Suggestions, search
│   └── system_monitor/test_system_monitor.py  # CPU, memory, disk, network, dashboard
```

### Key Fixtures

All fixtures are in `backend/tests/conftest.py`:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `app` | function | Real FastAPI app, all plugins active. Auto-detects DB: SQLite in-memory or PostgreSQL schema |
| `async_client` | function | `httpx.AsyncClient` via ASGI transport (real HTTP, no TCP) |
| `auth_headers` | function | Register user → return `{"Authorization": "Bearer <jwt>"}` (level=5) |
| `admin_headers` | function | Register user + DB-update level=0 → return admin JWT |
| `db_session` | function | Real async DB session from app's session factory |
| `oss_storage_dir` | function | Creates temp directory for OSS local storage, auto-cleaned after test |

`plugins/conftest.py` overrides `async_client` to build an app with only the target plugin (and its dependencies), providing test isolation.

### How Tests Work

1. **`app()` fixture** (function-scoped):
   - Calls `test_env.recommended_db_url()` to auto-detect database
   - PostgreSQL available → creates isolated `CREATE SCHEMA test_{uuid}`, runs all tables inside it, `DROP SCHEMA ... CASCADE` on teardown
   - SQLite fallback → creates in-memory SQLite with unique ID (per-test isolation guaranteed)
   - Calls `_build_app(db_url)` → runs `ensure_tables()` + seeds default config

2. **`async_client()` fixture** (function-scoped):
   - Creates `httpx.AsyncClient(transport=ASGITransport(app=app))`
   - Sends real HTTP requests through the full ASGI stack

3. **`auth_headers()` / `admin_headers()`**:
   - Actually call `POST /api/auth/register` + `POST /api/auth/login` on the real backend
   - `admin_headers` also updates the user's level to 0 in the database

4. **`oss_storage_dir` fixture** (function-scoped):
   - Creates `tmp_path / oss_storage` directory
   - Sets `OSS_STORAGE_DIR` env var so OSS service auto-discovers it
   - MinIO unavailable → OSS falls back to this local directory automatically

### External HTTP Mocking

Tests that trigger outbound HTTP requests must mock them using `pytest-httpx`:

```python
@pytest.mark.asyncio
async def test_external_api(self, async_client, auth_headers, httpx_mock):
    httpx_mock.add_response(
        url="https://api.example.com/data",
        json={"key": "value"},
    )
    resp = await async_client.get("/api/proxy/data", headers=auth_headers)
    assert resp.status_code == 200
```

- `httpx_mock` intercepts all `httpx.AsyncClient` / `httpx.Client` requests globally
- For non-httpx clients (e.g., `urllib3`, `aiohttp`), use `unittest.mock.patch`
- Plugin services that create internal `httpx.AsyncClient` instances are automatically intercepted

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

If the plugin's routes call external HTTP services, add the `httpx_mock` fixture and register mock responses.
If the plugin uses OSS local storage, add the `oss_storage_dir` fixture.

### Adding a Unit Test (Pure Logic)

```python
"""test_my_logic.py"""

from backend.plugins.my_plugin.services import MyCache

class TestMyCache:
    def test_cache_hit(self):
        cache = MyCache()
        cache.put("key", "value")
        assert cache.get("key") == "value"
```

No fixtures needed — pure functions only. Place in `backend/tests/unit/`.

### Database in Tests

| Environment | Strategy | Isolation |
|-------------|----------|-----------|
| Local dev (no Docker) | SQLite in-memory | Per-test: each `app()` fixture creates unique in-memory DB |
| CI / Docker | PostgreSQL via `ARCHE_TEST_DB_URL` | Per-test: `CREATE SCHEMA test_{uuid}` → all tables inside → `DROP SCHEMA CASCADE` |
| Explicit override | Set `ARCHE_TEST_DB_URL` env var | Follows PostgreSQL strategy |

- `ensure_tables()` runs at startup to create tables (catch-all for tables not in migration chain)
- Alembic migrations run automatically at startup (production path)

### OSS Storage in Tests

| Environment | Storage Backend | Cleanup |
|-------------|----------------|---------|
| Local dev | Local filesystem via `oss_storage_dir` fixture | `tmp_path` auto-cleaned by pytest |
| CI / Docker | MinIO (`bitnami/minio`) | Configured bucket + test-scoped paths |
| Fallback | OSS auto-falls back to local filesystem | `oss_storage_dir` handles it |

### Adding a New Fixture to conftest.py

Consider whether the fixture's behavior should change based on environment. If so, use `test_env`:

```python
@pytest_asyncio.fixture
async def my_service_fixture():
    if test_env.minio_available():
        # Real MinIO
        ...
    else:
        # Local fallback
        ...
```

### CI Pipeline

Tests run in two tiers:

1. **Unit tests** (`.github/workflows/test-unit.yml`) — Fast, no external services. SQLite + local storage. Runs on every PR.
2. **Integration tests** (`.github/workflows/test-integration.yml`) — Full stack with PostgreSQL + MinIO. Runs on merge to master and scheduled.

```yaml
# test-unit.yml — fast PR gate
- run: uv run pytest backend/tests/plugins/${{ matrix.plugin }}/ --tb=short --no-header

# test-integration.yml — full stack on master
services:
  postgres: postgres:16
  minio: bitnami/minio:latest
env:
  ARCHE_TEST_DB_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/arche_test
- run: uv run pytest backend/tests/ --tb=long
```

### Known Issues

- `request_log` plugin: routes return 500 because the `request_logs` table is not
  created by the initial Alembic migration. Fix: add migration or ensure `ensure_tables()`
  runs before the middleware intercepts requests.
- `system_monitor` plugin: template-related endpoints return 404 in isolated plugin tests
  because the `monitor` plugin's routes are registered under a separate prefix.

### Coverage Gate

Currently set to **0%** (new codebase). Raise incrementally as tests mature.

### Test Count Breakdown

| Layer | Approx. Count |
|-------|--------------|
| Unit tests | ~26 (13 logic + 13 test_env) |
| Core integration | ~60 |
| Plugin integration | ~170 |
| Edge / Security | ~40 |
| **Total** | **~290+** |
