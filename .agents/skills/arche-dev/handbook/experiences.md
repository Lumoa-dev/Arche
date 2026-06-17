# Experience Log

Lessons learned during Arche development — non-obvious pitfalls, design rationale, and reusable insights.

## How to Contribute

Log an entry immediately when you encounter something worth remembering.

### Entry Criteria

All four must apply:

- **Actual pain** — a bug we fixed, a mistake we made, an ambiguity that caused rework
- **Actionable** — the reader knows exactly what to do differently
- **Non-obvious** — common sense doesn't belong here
- **Reusable** — the same situation could plausibly recur

### Format

Keep it tight — one or two sentences per field:

```
### YYYY-MM-DD: Short imperative title

**What:** What to do (or what went wrong).

**When:** Context — module, trigger, preconditions.

**Why:** Root cause or rationale — the insight behind the fix.

**Lesson:** How to avoid this in the future.
```

---

## Entries

### 2026-06-12: Use `--body-file` in PowerShell for `gh issue create`

**What:** Pass issue body via a temp file (`--body-file`) instead of inline `--body`.

**When:** Creating GitHub Issues from Windows PowerShell with multi-line bodies containing backticks, quotes, or other special characters.

**Why:** PowerShell parses CLI arguments differently from bash — backticks and nested quotes in `--body` trigger syntax errors. `--body-file` bypasses argument parsing entirely.

**Lesson:** On Windows, always use `--body-file <tempfile>` for `gh issue create` with non-trivial bodies. Clean up the temp file afterward.

---

### 2026-06-12: Verify parent status before adding a GitHub Sub-issue

**What:** Check that an issue has no existing parent before adding it as a sub-issue.

**When:** Restructuring issues with GitHub Sub-issues — especially when migrating from an old parent to a new one.

**Why:** GitHub enforces one parent per sub-issue. Adding an issue that already has a parent returns `"Sub issue may only have one parent"`. Closing the old parent does NOT release the relationship.

**Lesson:** Before `addSubIssue`, run `removeSubIssue` from the old parent first. Design the issue hierarchy upfront to avoid mass migration.

---

### 2026-06-10: Never manually delete Alembic migration files

**What:** Don't delete `.sql` migration files under `backend/plugins/*/alembic/`.

**When:** Cleaning up files — migration directories can look like "old" or "generated" files that seem safe to remove.

**Why:** Alembic relies on a complete migration chain to reach the current database version. Missing any file breaks the version chain and prevents startup.

**Lesson:** Migration files are infrastructure, not cache. Use Alembic's own squashing/merging commands if cleanup is needed.

---

### 2026-06-10: CI can't run `generate:api` without a live backend

**What:** In CI, verify `generated.d.ts` exists instead of re-running `npm run generate:api`.

**When:** Frontend CI pipeline — the step that ensures API types are in sync.

**Why:** `npm run generate:api` requires a running backend on port 8000 to fetch the OpenAPI schema. CI doesn't run the backend, so the command would fail. The committed file is the source of truth.

**Lesson:** Build-time code generation that depends on external services needs a CI fallback strategy. File-existence checks are simple and effective.

---

### 2026-06-05: Replace naive-ui components with self-built Ar components

**What:** Build custom Ar* components (ArButton, ArCard, etc.) instead of wrapping or patching naive-ui components.

**When:** A third-party library's rendering behavior (slot wrappers, opinionated CSS, undocumented DOM structure) conflicts with the project's design system.

**Why:** naive-ui's extra wrapper elements cause hard-to-fix layout bugs (e.g., `<span>` wrappers breaking flex alignment). Self-built components give full control over rendering and design language.

**Lesson:** For UI-consistent projects, a self-built component library pays off in the long run. Migrate incrementally — one component at a time, not a big bang.

---

### 2026-06-12: Remove custom `event_loop` fixture for Python 3.13 E2E tests

**What:** Remove the custom function-scoped `event_loop` fixture from E2E conftest.py that called `asyncio.set_event_loop()`.

**When:** Python 3.13+ with pytest-asyncio 1.x in E2E tests using pytest-playwright (sync API).

**Why:** Python 3.13's `asyncio.Runner` has an internal state machine (`IDLE → RUNNING → IDLE`). The custom fixture's `asyncio.set_event_loop()` interfered with the Runner's loop management, causing `Runner.run()` to raise `RuntimeError: Runner.run() cannot be called from a running event loop`. The default fixture behavior (without `set_event_loop`) works correctly.

**Lesson:** Avoid overriding `event_loop` fixture with `asyncio.set_event_loop()` in Python 3.13+. Let pytest-asyncio manage the loop. This is a common pitfall when upgrading from Python 3.12 to 3.13.

---

### 2026-06-12: Don't restrict `pull_request.branches` in CI for branch-based workflows

**What:** Remove `branches: [master]` from `pull_request` trigger in CI workflow — or use a broader branch pattern like `branches: ['*']`.

**When:** A multi-level branching strategy (upstream/downstream) where downstream fix branches create PRs targeting an upstream branch, not `master`.

**Why:** `pull_request`'s `branches` filter matches the **target** branch of the PR, not the source. If downstream PRs target an upstream branch (not `master`), the CI workflow silently skips them. This causes a false sense of security — no check run appears, no failure notification.

**Lesson:** Unless there's a strong reason to restrict, omit `branches` from `pull_request` triggers entirely. Downstream jobs with `image_tag` guards already prevent accidental builds/deploys on non-master PRs. If you do need restrictions, use `branches: ['*']` to be explicit that all target branches are included.

---

### 2026-06-12: Prefer self-built ArPopconfirm over NPopconfirm workarounds

**What:** Build `ArPopconfirm` as a `src/components/ui/` component to replace `NPopconfirm`.

**When:** A third-party component has a structural rendering issue that can't be cleanly fixed with CSS.

**Why:** CSS hacks for naive-ui's DOM structure are fragile and don't fix the root cause. A self-built component (`position: absolute` + `transform` + Vue `Transition`) is fully controllable and matches the glassmorphism design system.

**Lesson:** When a library component fights your layout, replace it rather than patch around it. Positioning and transition utilities are worthwhile shared infrastructure.

---

### 2026-06-13: Enforce three-layer frontend architecture with CSS responsibility separation

**What:** Frontend code must follow a strict three-layer architecture: Base Components (pure UI, no API, no business), Business Components (composable-encapsulated API, fixed CSS specs), Pages (layout + permission only, near-zero CSS).

**When:** Any Vue component creation or modification in the frontend.

**Why:** Previous frontend had no clear layer boundaries — CSS was scattered across all levels, API calls were mixed into everything, and business logic leaked into UI primitives. This made the codebase unpredictable and hard to refactor.

**Lesson:** Define layer boundaries upfront with iron-clad rules and CR checklists. Base components use CSS variables for theming. Business components fix all scene specs in CSS (normal/empty/loading/error). Pages are forbidden from having more than 5 lines of CSS or any non-layout properties. API calls in `.vue` files are banned — use composables instead.

---

### 2026-06-15: First user gets P0 — seed `PageComponentPermission` at registration time

**What:** When the first registered user becomes P0 (level=0), pre-fill `page_component_permissions` with all pages set to visible=True. New pages added later must be added to the seed list or configured via the permission editor.

**When:** First-user registration flow — `AuthService.register()` already detects first user and sets level=0, but the empty `page_component_permissions` table blocks everything including P0.

**Why:** The route guard (`guard.ts`) calls `canAccessPage()` which checks `permissionCache[level][pageName]`. An empty table returns `{}` so `canAccessPage('create')` returns `false` for everyone, including P0. The seed ensures P0 has full access immediately.

**Lesson:** Any change to the list of frontend pageNames must be mirrored in the seed list in `AuthService.register()`. Search for `all_pages = [` in `backend/plugins/auth/services.py` and add the new page. Alternatively, use the permission editor UI to add new pages for any level.

---

### 2026-06-15: Permission bus — backend-driven page-level permission with frontend subscription

**What:** Implement page-component level permission control using a backend-driven JSON mapping table, consumed by a frontend permission bus.

**When:** Building authorization for the Arche platform. Previous approach used static permission codes (`permission: 'auth:users:list'`) hardcoded in both frontend routes and `v-permission` directives — changing permissions required redeploy.

**Why:** A level-based (0-10) system with a `PageComponentPermission` DB table is simpler to manage than RBAC with named roles. The permission bus pattern (backend stores `{pageName: {componentName: boolean}}`, frontend fetches at runtime) eliminates hardcoded permissions entirely. Key insight: if any component in a page is visible, the page is accessible — this maps naturally to route guards and sidebar rendering.

**Lesson:** For permission systems in personal platforms, prefer level-based access over role-based. Store the page-component mapping in a single DB table with unique constraint on `(level, page_name, component_name)`. Frontend should treat permissions as external data fetched at login (with 5-min TTL), not as compile-time constants. The `v-permission` directive format `page.component` maps cleanly to this model.

---

### 2026-06-16: Three-layer defense for Nginx real IP passthrough

**What:** Write `get_real_ip(request)` utility to get the real client IP, priority `X-Real-IP` → `X-Forwarded-For` first IP → `request.client.host`.

**When:** Behind nginx reverse proxy, `request.client.host` always returns the Docker internal IP (e.g., `172.x.x.x`), causing login rate-limiter and history to record internal addresses.

**Why:** Three-layer defense design:
- nginx.conf already sets `proxy_set_header X-Real-IP $remote_addr` (layer 1)
- uvicorn `--proxy-headers` makes the ASGI layer trust proxy headers (layer 2)
- `get_real_ip()` reads the `X-Real-IP` header at the application layer (layer 3)
- Three layers guarantee real IP acquisition regardless of deployment environment

**Lesson:** When replacing `request.client.host`, audit all `client_ip` usage chains (routes → services → models) to ensure consistency. Put `get_real_ip()` in `middleware.py` alongside `get_current_user()` so all plugins can call it uniformly.

---

### 2026-06-24: Name CI/CD workflow files with elementary-level English, split tests by type

**What:** Rename all workflow files and job names to the most basic English words (check / test / scan / build / deploy). Avoid advanced terms like adversarial / codeql / bandit / validate / sync. Split tests into 3 files by type.

**When:** Refactoring the CI/CD system. The old system used advanced English vocabulary (e.g., "adversarial"), which is unfriendly to non-native English maintainers. The single `test.yml` was 331 lines carrying 4 test modes.

**Why:** Simple words lower the reading bar. Splitting files keeps each workflow single-responsibility. Matrix parallelism is preserved (each plugin/directory still runs in parallel), but individual files are smaller and easier to maintain.

**Lesson:** Naming principle: assume the reader is in elementary school. Use words they can understand at a glance. adversarial → attack-test, codeql/bandit → scan-code/scan-py. Split tests into three files (unit / integration+attack / E2E), each 80-120 lines. `ci.yml` orchestrates only, contains no logic. Attack tests belong under "test", classified in `test-integration.yml`, not a security file.

---

### 2026-06-24: Run all test directories in test-unit.yml without incremental detection

**What:** Remove all `git diff` logic and frontend source-to-test directory mapping. `find-changes` uses just two lines `ls -1d */*/` to enumerate all test directories and run them all. Matrix parallelism relies on GitHub Actions `strategy.matrix`.

**When:** Simplifying `test-unit.yml` again. The first refactor added git diff incremental detection, but:
- `pytest -n auto` already parallelizes — full run isn't much slower than incremental
- git diff logic + case mapping took 70 lines, maintenance cost outweighed benefit
- Matrix jobs are already parallel — CI can handle new directories

**Why:** When speed isn't the bottleneck, complexity is debt. Full scan + matrix parallelism = 7 lines of bash, zero branches, zero mappings. Adding a new plugin or test directory requires no CI changes — auto-discovery works out of the box.

**Lesson:** Don't write dozens of lines of change-detection logic in CI to save a few seconds. Start with the simplest full-scan approach; optimize only when it's actually slow. `ls -1d` + `jq` to JSON is the standard pattern for GitHub Actions matrix auto-discovery.

---

### 2026-06-24: Extract report-fail.yml as a reusable failure notification workflow

**What:** Extract the "test failure → create Issue + create fix branch" logic from `test-integration.yml` into a standalone `report-fail.yml` reusable workflow. Supports five inputs: title / labels / artifact-name / create-fix-branch / branch-prefix.

**When:** During CI/CD refactoring, `test-integration.yml` had `test-attack` and `alert-fail` jobs each inlining their own Issue-creation scripts — duplicate code mixed in with test logic.

**Why:** Failure notification is a separate concern and shouldn't live inside test files. After extraction:
- Any workflow can use `uses: ./.github/workflows/report-fail.yml` for one-click alerting
- `test-integration.yml` focuses on test logic, shrinking from 131 to 65 lines
- New alert scenarios (build failure, deploy failure) don't need to duplicate scripts

**Lesson:** Split CI files by **responsibility**, not by "pipeline stage". Cross-cutting concerns like alerting, notification, and reporting naturally belong in their own files. Use `workflow_call` + input parameters for reusability. Pass labels as comma-separated strings instead of JSON arrays — it's simpler.

---

### 2026-06-16: Use `--body-file` for `gh pr create` under PowerShell to avoid backtick escaping

**What:** Use `--body-file <tempfile>` to pass PR body content instead of inline `--body "..."`.

**When:** Creating a GitHub PR from Windows PowerShell with a body that contains Markdown backticks (`).

**Why:** Two things conspire to break the content:
- PowerShell's backtick (\`) is the escape character itself (same role as `\` in bash). Every \` in a CLI argument string gets consumed by PS
- The chain PS → Git Bash → gh CLI is too long — phantom characters appear (backticks become backslashes, leading letters like `b` in `backend` get swallowed)
- `--body-file` reads from disk, completely bypassing shell argument parsing — content arrives intact

**Lesson:** On Windows, any `gh pr create` / `gh issue create` call with multi-line or special-character body should use `--body-file <tempfile>` + clean up the temp file afterward.

---

### 2026-06-16: Remove dangling jobs from CI/CD workflows

**What:** Cleaned up all unused and conditional-skip jobs across CI/CD:
- `test-unit.yml`: removed `find-changes` (separate scan job), removed `show-cover` (only triggered on schedule), scan logic inlined into each test job via shell loop
- `test-integration.yml`: removed `alert-schedule` and `alert-fail` (conditional failure-only jobs that called report-fail.yml)
- `deploy.yml`: removed `validate`/`sync-check`/all 4 deploy path variants/`summary` — kept only single SSH deploy
- `report-fail.yml`: deleted entirely (130 lines, only called by removed alert jobs)
- `label-sync.yml`: deleted entirely (90 lines of JS, unrelated to CI pipeline)

**When:** Refactoring CI/CD. The 13-file pipeline had jobs that only ran conditionally (failure, schedule, webhook mode) or were leftover from incremental-detection logic.

**Why:** Conditional jobs (`if: failure()`, `if: github.event_name == 'schedule'`) create "dangling" jobs that show as skipped in every run. They add visual noise without value — failure notification via auto-Issue/auto-branch is overkill for a personal project; checking Actions logs is sufficient. `find-changes` as a separate job required matrix dependencies and `if` guards — inlining the loop eliminates the dependency chain.

**Lesson:** In GHA, a job that conditionally skips on every run is noise, not value. The three patterns to eliminate: (1) separate job just for matrix generation — inline the loop instead; (2) failure notification jobs — rely on Actions UI; (3) mode-dispatching jobs (SSH vs webhook, sync vs no-sync) — pick one mode and delete the rest. Result: 13 files → 10 files, ~650 lines → ~300 lines.

---

### 2026-06-16: Fix integration test "Event loop is closed" caused by missing ip_ban models import and duplicate indexes

**What:** Three fixes for integration test failures:
1. Added `from backend.plugins.ip_ban import models as _ip_ban_models` to `module_db` test fixture so `ip_bans` table is created
2. Added explicit `ip_ban` service mock in `db_container` fixture that returns `is_ip_banned=False`, preventing the middleware from blocking test requests
3. Removed duplicate `index=True` from `ip_or_cidr` and `ban_id` columns in `IpBan`/`IpBanLog` models — they already had explicit `Index` entries in `__table_args__`

**When:** Running integration tests (`pytest backend/tests/integration/ -n auto`). The `test_app` fixture activates all plugins including `ip_ban`, whose middleware and models weren't accounted for in test fixtures.

**Why:** Three root causes conspired:
- `module_db` fixture imported models from every plugin except `ip_ban` → `ip_bans` table never created → teardown `DELETE FROM ip_bans` crashed with "no such table"
- `container` is a `MagicMock`, so `container.is_available("ip_ban")` returned truthy, and the fallback `AsyncMock` service returned `is_ip_banned=True` → all requests got 403
- `index=True` on a column + explicit `Index` with the same name in `__table_args__` = SQLite tries to create the index twice → `OperationalError: index already exists`
- These errors cascaded into "Event loop is closed" because the event loop was left in a bad state after the SQLite crash

**Lesson:** When adding a new plugin with models and middleware, audit all test fixtures:
1. `module_db` — add the new plugin's models import so `create_all` picks them up
2. `db_container.get_service` — add explicit handling for the new plugin's service (even if mocked)
3. Check model indexes — never combine `index=True` on a column with an explicit `Index()` in `__table_args__` for the same column

---

### 2026-06-16: Real integration tests must trigger lifespan events or tables won't exist

**What:** `httpx.AsyncClient(app=app)` with `ASGITransport` does NOT trigger FastAPI lifespan startup events. The `on_event("startup")` hook (Alembic migration → ensure_tables → seed config) never runs, so middleware that queries tables (`ip_ban`, `request_log`) crashes with "no such table".

**When:** Rewriting all backend tests as real integration tests — no mocks, real FastAPI app, real database.

**Why:** HTTPX's `ASGITransport` is designed for lightweight ASGI testing and doesn't manage lifespan by default. FastAPI's `on_event` decorators hook into Starlette's lifespan protocol, which only runs within a lifespan context manager. Using `httpx.AsyncClient` without a lifespan context means startup tasks never execute.

**Lesson:** Two solutions: (1) Use `fastapi.testclient.TestClient` which triggers lifespan automatically → subsequent `httpx.AsyncClient` tests work because tables are already created. (2) Keep the `app` fixture session-scoped and use `TestClient` context manager during fixture setup to trigger startup.

---

### 2026-06-16: `require_level(0)` routes need admin_headers fixture, not auth_headers

**What:** Routes decorated with `@require_level(0)` return 403 for tokens from `auth_headers` fixture (which creates a level-5 user).

**When:** Writing plugin tests for admin-only endpoints (ip_ban, request_log, config_mgmt).

**Why:** `auth_headers` fixture creates a normal user who gets level 5. The `admin_headers` fixture must explicitly set level=0 via database UPDATE after registration, because the first-user-get-level-0 logic only applies to the very first user ever registered.

**Lesson:** Two-tier auth fixtures: `auth_headers` (level-5 regular user for testing 403 forbidden), `admin_headers` (level-0 admin via DB update after registration).

---

### 2026-06-16: `/api/ping` must be in AuthMiddleware.PUBLIC_PATHS

**What:** Health check endpoint `/api/ping` returned 401 because `AuthMiddleware` treats all non-public routes as requiring authentication.

**When:** Writing real integration tests that hit `/api/ping` without auth headers.

**Why:** The `AuthMiddleware` only whitelists `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`. Everything else requires a valid JWT. A health check endpoint should always be public.

**Lesson:** Added `/api/ping` to `AuthMiddleware.PUBLIC_PATHS` — health checks are infrastructure, not application logic.

---

### 2026-06-17: Use pytest-httpx to mock external HTTP in integration tests

**What:** When an integration test triggers outbound HTTP (e.g., GitHub raw content proxy), mock it with `pytest-httpx`'s `httpx_mock` fixture instead of marking the test with `@pytest.mark.real` and skipping in CI.

**When:** Writing tests for plugins that proxy or fetch external URLs — github_proxy, crawler, cloud_integration, oss, ip_ban.

**Why:** `@pytest.mark.real` tests are always skipped by default, so their coverage is effectively zero. `pytest-httpx` intercepts all `httpx.AsyncClient`/`httpx.Client` requests globally, including clients created internally by services (e.g., `HttpProxyService.proxy_raw_content` creates its own `httpx.AsyncClient`). For non-httpx HTTP clients (`urllib3`, `aiohttp`), use `unittest.mock.patch` instead.

**Lesson:** Default to `pytest-httpx` for any integration test that would otherwise need network access. The `httpx_mock` fixture is autowired by pytest — no conftest registration needed. For services that create their own `httpx.AsyncClient` internally, the mock still intercepts because it patches at the transport layer.

---

### 2026-06-17: Distinguish test layers — unit, integration, edge/security

**What:** Organize backend tests into three directories with clear boundaries: `unit/` (pure logic, no ASGI/DB), `core/` + `plugins/` (real ASGI integration), `edge_cases/` (boundary conditions + attack vectors).

**When:** Restructuring the test suite. Previously all tests were "real integration tests" with no mock, but some code (CacheEntry, URL parsing, rate limiter logic) is pure enough to test without the ASGI stack — saving ~74s per run for 13 fast tests.

**Why:** Unit tests run in <0.5s vs integration tests taking 3-8s each. Separating them makes the quick feedback loop faster for pure logic changes. Edge/security tests are a distinct concern — they verify the system doesn't crash or leak under attack, not that features work correctly.

**Lesson:** Enforce the boundary in the directory structure, not in comments. `unit/` tests import service classes directly and construct minimal fakes for dependencies (e.g., `FakeContainer` with `get()` returning config). They never `from conftest import app` or use `async_client`.

---

### 2026-06-17: First-time registration gives level 0 — mass assignment test can't assert `level != 0`

**What:** In `test_security.py::TestMassAssignment::test_cannot_set_own_level`, attempting to register with `level: 0` succeeds and the resulting user has level 0 — not because the request body was honored, but because the first registered user in any test session gets level 0 by auth service logic.

**When:** Writing a stronger assertion that registration with `level: 0` should not result in `level: 0`.

**Why:** The auth service grants level 0 to the first-ever user as a bootstrap mechanism. The `level` field in the request body is ignored (mass assignment protection works), but the first-user promotion happens after the field is already discarded. Any test of mass assignment must avoid asserting on the resulting level value — check instead that extra fields don't cause a 500.

**Lesson:** When testing mass assignment protection in a system with first-user promotion, don't assert on the resulting field value. Check that the API doesn't crash and that the extra fields are silently ignored. Document the first-user quirk in the test comment.

---

### 2026-06-17: Test environment auto-detection — `test_env.py` as the foundation layer

**What:** Create `backend/tests/test_env.py` as the test infrastructure's "eyes" — automatically detects Docker/WSL/CI environment and PostgreSQL/MinIO service availability, then adapts the test configuration accordingly.

**When:** Building the testing foundation layer. Previously, switching between SQLite and PostgreSQL required manual `ARCHE_TEST_DB_URL` setting, and OSS tests always skipped because the storage directory didn't exist.

**Why:** A unified environment detection layer eliminates human error in test configuration. Docker containers detect themselves via `/.dockerenv`, CI via environment variables, service availability via port probes. The detection output is printed at the start of every test run, making the test configuration transparent.

**Lesson:** The detection module must be pure Python stdlib — no pytest fixtures, no application imports — so it can be imported at module level in conftest.py before any fixtures initialize. Cache detection results (via `_CACHE` dict) since they're read-heavy but don't change during a test run.

---

### 2026-06-17: PostgreSQL test isolation — per-test schema for CI/Docker

**What:** When PostgreSQL is available, each `app()` fixture creates an isolated schema (`CREATE SCHEMA test_{uuid}`), runs all tables inside it, and drops it on teardown (`DROP SCHEMA ... CASCADE`). This matches SQLite in-memory's per-test isolation guarantee.

**When:** Running integration tests against a real PostgreSQL database. Without schema isolation, tests using the same fixed database (`arche_test`) can conflict — parallel test runs or sequential tests that leave residual data break each other.

**Why:** SQLite in-memory gives per-test isolation for free (each `app()` creates a brand-new database). PostgreSQL needs an explicit equivalent. Schema-level isolation is lighter than database-level (no connection pool reconfiguration) and can be implemented purely in conftest.py without changing application code.

**Lesson:** Use `isolation_level="AUTOCOMMIT"` for the schema-creation engine (DDL outside transactions). Set `search_path` in the connection URL so all subsequent `Base.metadata.create_all` and queries land in the right schema. Always `DROP SCHEMA ... CASCADE` on teardown — never leave test schemas behind.

---

### 2026-06-17: OSS local storage in tests — auto-create temp dir via fixture

**What:** Added `oss_storage_dir` fixture that creates a pytest `tmp_path` subdirectory and sets `OSS_STORAGE_DIR` env var. The OSS service's `_get_local()` backend auto-discovers this directory, so upload tests work without MinIO. Replaced `pytest.skip("OSS storage 目录未初始化")` with the fixture dependency.

**When:** OSS plugin tests — the `test_upload_image` test always skipped because no storage directory existed in the test environment.

**Why:** The OSS service already had automatic fallback from MinIO → local filesystem (`_get_minio()` → `_get_local()`). The missing piece was just a writable directory. pytest's `tmp_path` provides automatic creation + cleanup, which pairs perfectly with the OSS fallback chain.

**Lesson:** When a service already has graceful fallback, the test infrastructure just needs to provide the fallback target. The `oss_storage_dir` fixture pattern can be reused for any plugin that writes to local filesystem in tests. Name the fixture clearly so plugin tests know they can depend on it.
