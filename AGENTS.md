# AGENTS.md — AI Agent Operating Manual

This document is the operating manual for AI agents working on the Arche project. It defines the language protocol, available skills, rule files, standard operating procedures, and project reference.

---

## 1. Language Protocol

Arche spans multiple language contexts. Adhere strictly to the following:

| Context | Language | Notes |
|---------|----------|-------|
| User communication | **Follow the user's language** | If the user writes Chinese, respond in Chinese. If English, respond in English. |
| Skill files (SKILL.md) | **English** | AI-facing instructions — English is more stable and precise |
| Experience log (experiences.md) | **English** | Structured entries, AI-friendly |
| Project standards (standards.md) | **English** | Policy declarations, AI-friendly |
| Technical handbooks (handbook/*.md) | **English** | Consistent with the skill ecosystem |
| Code comments | **Chinese** | Project immutable rule |
| Git commit messages | **Chinese** | Conventional Commits convention |
| AGENTS.md | **English** | Consistent with the rest of the skill ecosystem |

---

## 2. Skill Directory

Skills are registered under `.trae/skills/`. The agent should determine which skill to load based on the task context.

| Skill | File | Trigger |
|-------|------|---------|
| **arche-dev** | `.trae/skills/arche-dev/SKILL.md` | **Default skill** — every Arche development task (architecture, coding, testing, CI/CD, docs, etc.) must load this skill first |
| **commands** | `.trae/skills/commans/SKILL.md` | User issues a slash-command-style request (e.g., "fix this function", "explain this code", "generate tests") |

> **Note**: `arche-dev` is the primary skill — **load it at the start of every task**. `commands` is a quick-command registry, triggered only when the user gives a slash-command-style instruction.

---

## 3. Rule Index

Workflow rules are defined under `.trae/rules/`. The agent must follow them in the applicable scenarios.

| Rule File | When to Apply |
|-----------|---------------|
| `git-commit-message.md` | **Every commit** — Conventional Commits format, type/scope list, language requirement |
| `issue-fix-workflow.md` | **Picking up an Issue for code fix** — full workflow from reading the Issue to submitting a PR |
| `issues-management-workflow.md` | **Managing Issues without writing code** — Code Review, triage, close/split decisions |

---

## 4. Standard Operating Procedure (SOP)

### 4.1 General Development Task

```
Step 1: Load the arche-dev skill
          └─ Read SKILL.md for immutable rules and handbook index

Step 2: Pre-read mandatory documents
          ├─ experiences.md  — check for relevant lessons and pitfalls
          └─ standards.md    — review project conventions (labels, templates, formats)

Step 3: Read the relevant handbook based on task type
          ├─ Architecture/startup  →  architecture.md
          ├─ Backend development   →  backend.md
          ├─ Frontend development  →  frontend.md
          ├─ Plugin development    →  plugin-dev.md
          ├─ Testing               →  testing.md
          ├─ CI/CD                 →  cicd.md
          └─ Issue management      →  issue-management.md

Step 4: Execute the task (follow applicable rule files)

Step 5: Distill experience
          └─ If something worth remembering was learned, append to experiences.md
```

### 4.2 Issue Fix Task

In addition to 4.1:

```
Step 2.5: Read issue-fix-workflow.md
           ├─ gh issue view <N> to read the full Issue
           ├─ Code Review to verify the problem
           ├─ Check branch environment (create fix/issue-* from master)
           └─ Submit PR per convention after fixing
```

### 4.3 Issue Management Task (no code)

```
Step 1: Read issues-management-workflow.md
Step 2: Code Review → triage
          ├─ Already fixed → close Issue and comment
          ├─ Deeper issue found → comment with analysis
          └─ Compound issue → split into sub-issues
```

---

## 5. Project Reference

### 5.1 Layout

| Package | Directory | Package Manager | Entry |
|---------|-----------|-----------------|-------|
| Backend | `backend/` | `uv` (root `pyproject.toml`) | `backend/main.py` → `uvicorn backend.main:app` |
| Frontend | `frontend/` | `npm` (`frontend/package.json`) | `frontend/src/main.ts` → `npm run dev` |

### 5.2 Essential Commands

```bash
# ── Install ──
uv sync                        # backend
cd frontend && npm install     # frontend

# ── Dev servers ──
uv run uvicorn backend.main:app --reload   # backend (port 8000)
cd frontend && npm run dev                 # frontend (port 5173)

# ── Lint / format ──
uv run ruff check backend/                 # backend lint
uv run ruff format backend/                # backend format (apply)
uv run python scripts/lint_rules.py --fail backend/   # custom lint
cd frontend && npm run lint                # frontend lint
cd frontend && npm run format              # frontend format

# ── Type-check ──
cd frontend && npm run type-check          # vue-tsc --noEmit

# ── Build ──
cd frontend && npm run build               # frontend → frontend/dist/

# ── Tests ──
uv run pytest                              # all backend tests
uv run pytest --no-cov -ra --tb=short      # quick backend test
cd frontend && npm run test:run            # frontend tests (single run)

# ── API type generation ──
cd frontend && npm run generate:api        # OpenAPI → TS types
```

### 5.3 Architecture: Microkernel + Plugins

- **`backend/core/`** — the never-changing kernel. Boot sequence: Logging → DB init → ServiceContainer → Plugin activation (DAG-sorted) → Middleware → Startup hooks (Alembic auto-migration, schema validation, config seeding)
- **`backend/plugins/`** — all features are self-contained plugins, auto-discovered at startup. Each has its own `__init__.py` / `routes.py` / `services.py` / `models.py`

### 5.4 Key Quirks

- **Alembic migrations run automatically at startup** — no separate CLI step
- **Database**: SQLite + aiosqlite (dev), PostgreSQL + asyncpg (production)
- **Config layering**: `.env` < environment variables < database (with TTL cache)
- **Frontend code splitting by role**: `blog/` (public), `platform/` (authenticated), `admin/` (admin)
- **Backend serves frontend**: dev via reverse proxy, production via Nginx
- **No lambda, no nested comprehensions** — enforced by custom lint

### 5.5 Frontend Component Layers

| Layer | Directory | Purpose | CSS Rule |
|-------|-----------|---------|----------|
| UI primitives | `src/components/ui/` | ArButton, ArCard, ArTable, ArInput, etc. | 大量 CSS — 高度完备的通用组件 |
| Business components | `src/components/widgets/` | PostCard, PostEditor, CommentList, RichTextEditor, etc. | 少量 CSS — 业务场景固定规格 |
| Pages | `src/views/` | 页面级组件 | **0 CSS** — 无任何 `<style>` 标签 |
| Layouts | `src/layouts/` | BaseLayout, BlogShell, PlatformShell, ConsoleLayout, etc. |

### 5.6 Frontend CSS 红线规则

- **页面 0 CSS**：禁止 `<style>` 标签，布局用 ArVBox / ArHBox 等基础布局组件
- **业务组件少量 CSS**：仅限业务场景固定规格，不超过 20 行
- **布局必须用 Ar 布局原语**：ArVBox / ArHBox / ArSpacer / ArGrid，禁止手写 flex/grid
- **缺失组件须汇报**：基础组件不存在的 UI 模式须汇报后再决定，禁止用 CSS 临时实现
- **CR 发现违规直接打回**

### 5.7 CI Pipeline

`backend-lint` → `backend-test` → `frontend-check` → `frontend-test` → `security-scan` → `gate` → (`build` → `deploy` + `tag-release`)

- Tags `v*` trigger build + deploy
- PR merges to `master` auto-increment patch version, then build + deploy
- Plain pushes to `master` (no tag) run lint/test only

---

## 6. Related Documents

| Document | Path |
|----------|------|
| Project overview | `README.md` |
| Contributing guide | `CONTRIBUTING.md` |
| Backend test strategy | `backend/tests/TEST_STRATEGY.md` |
| Frontend API call policy | `frontend/docs/api-call-policy.md` |
| Frontend module structure | `frontend/src/README.md` |
| Architecture docs | `docs/` (Chinese) |
