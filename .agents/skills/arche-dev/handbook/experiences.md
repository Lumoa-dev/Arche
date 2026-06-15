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

### 2026-06-24: CI/CD 工作流文件用小学级英文命名，按类型拆分测试

**What:** 工作流文件名和 job 名全部改用最基础的英文词汇（check / test / scan / build / deploy），避免 adversarial / codeql / bandit / validate / sync 等高级词。测试按类型拆成 3 个文件。

**When:** 对 CI/CD 体系进行重构升级时。旧体系用了大量高级英文词汇（adversarial「对抗性」），对非英语母语的维护者不友好；test.yml 一个文件 331 行承载 4 种测试模式，过于臃肿。

**Why:** 简单词汇降低阅读门槛，拆分文件让每个工作流职责单一。矩阵测试能力不变（每个 plugin/目录仍并行），但文件更小更好维护。

**Lesson:** 命名原则：假设读者是小学三年级，只用他们能一眼看懂的词。adversarial → attack-test，codeql/bandit → scan-code/scan-py。测试按单元/集成+攻击/E2E 拆 3 个文件，每个文件 80-120 行，ci.yml 只做编排不写逻辑。对抗测试属于「测试」，归入 test-integration.yml 而非 security 文件。

---

### 2026-06-24: test-unit.yml 全量扫目录跑，不做增量检测

**What:** 删掉所有 git diff 逻辑和前端 source→test 目录映射。`find-changes` 只用两行 `ls -1d */*/` 扫出所有测试目录，全量跑。矩阵并行靠 GitHub Actions 的 `strategy.matrix`。

**When:** 再次简化 test-unit.yml 时。第一次重构用 git diff 做了增量检测，但发现：
- pytest -n auto 已经多线程，全量跑不比增量慢多少
- git diff 逻辑 + case 映射写了 70 行，维护成本 > 收益
- 矩阵本来就是并行 job，加个新目录 CI 扛得住

**Why:** 速度不是瓶颈时，复杂度就是负债。全量扫目录 + 矩阵并行 = 7 行 bash，无分支无映射。加新 plugin 或新测试目录什么也不用改，CI 自动发现。

**Lesson:** 不要在 CI 里为「省几秒」写几十行变更检测逻辑。先用最简单的全量方案跑起来，真慢了再优化。`ls -1d` + `jq` 转 JSON 是 GitHub Actions 矩阵自动发现的标配写法。

---

### 2026-06-24: 提取 report-fail.yml 可复用失败告警工作流

**What:** 把「测试失败 → 建 Issue + 建 fix 分支」的逻辑从 test-integration.yml 抽成独立的 report-fail.yml 可复用工作流。支持 title/labels/artifact-name/create-fix-branch/branch-prefix 五个输入。

**When:** CI/CD 重构时发现 test-integration.yml 里 test-attack 和 alert-fail 两个 job 各自内联写了一份 Issue 建告脚本，代码重复且混在测试逻辑里。

**Why:** 失败告警是独立职责，不应该和测试混在同一个文件里。抽成 report-fail.yml 后：
- 任何工作流都可以 `uses: ./.github/workflows/report-fail.yml` 一键告警
- test-integration.yml 专注测试逻辑，从 131 行减到 65 行
- 新增告警场景（比如 build 失败、deploy 失败）不需要重复写脚本

**Lesson:** CI 文件按**职责**拆分，不是按「流水线阶段」。告警、通知、报告这类横切关注点天然应该独立成文件。用 `workflow_call` + 输入参数保持通用性。建 Issue 的 labels 用逗号分隔字符串传入比 JSON 数组更省心。
