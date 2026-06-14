# Testing Strategy

## Backend (pytest)

### Running Tests

```bash
uv run pytest                              # All tests (coverage gate: 40%)
uv run pytest --no-cov -ra --tb=short      # Quick run, no coverage
uv run pytest -m "not integration"         # Unit only
uv run pytest backend/tests/unit/ -v       # Unit tests by directory
uv run pytest backend/tests/integration/ -v # Integration tests only
uv run pytest -k "auth" -v                 # Keyword filter
uv run pytest backend/tests/unit/test_auth.py -v  # Single file
```

### Test Structure

```
backend/tests/
├── conftest.py            # Global fixtures (session, client, db)
├── unit/                  # Unit tests (no external deps)
│   ├── test_*.py
│   └── conftest.py        # Unit-specific fixtures
└── integration/           # Integration tests (DB, API calls)
    ├── test_*.py
    └── conftest.py        # Integration-specific fixtures
```

### Key Fixtures

See `backend/tests/TEST_STRATEGY.md` for the complete fixture inventory. Key fixtures include:

- `async_client` — test HTTP client for FastAPI app
- `db_session` — async DB session (in-memory SQLite with `StaticPool`)
- `auth_headers` — pre-authenticated JWT headers

### Database in Tests

Tests use in-memory SQLite with `StaticPool` to share the connection:

```python
from sqlalchemy.pool import StaticPool

engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
```

This avoids cross-session isolation issues common with in-memory SQLite.

### Coverage Gate

The minimum coverage threshold is **40%**. Below this, CI fails.

### Test Marker Categories

| Marker | Description |
|--------|-------------|
| (none) | Unit test (default) |
| `integration` | Integration test — requires DB or external services |

## Frontend (vitest)

### Running Tests

```bash
cd frontend && npm run test:run    # Single run
cd frontend && npm run test        # Watch mode
```

### Environment

- vitest with jsdom environment
- Test files co-locate with source: `ComponentName.spec.ts`

### What to Test

- Component rendering and user interactions
- Pinia stores
- API service layer
- Route guards

## When to Write Tests

- New feature: add tests for the feature
- Bug fix: add a test that reproduces the bug before fixing
- Refactoring: ensure existing tests pass, add tests for changed behavior
