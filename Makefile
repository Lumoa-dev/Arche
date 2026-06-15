# ── Arche 开发底座：一键任务 ──────────────────────────────────
# 用法：make <target>
#    make install      安装所有依赖
#    make dev          启动前后端开发服务器
#    make lint         运行所有 linter
#    make format       格式化所有代码
#    make format-check 检查格式是否合规
#    make type-check   运行所有类型检查
#    make test         运行所有测试
#    make build        构建前端
#    make check        本地质量门（format-check → lint → type-check → test）
#    make clean        清理缓存
#    make precommit    手动触发 pre-commit 全量检查

.PHONY: install dev lint format format-check type-check test build check clean precommit

# ── 安装 ─────────────────────────────────────────────────────
install:
	uv sync
	cd frontend && npm install

# ── 开发服务器 ────────────────────────────────────────────────
dev:
	@echo "==> 启动后端 (http://localhost:8000)"
	@echo "==> 启动前端 (http://localhost:5173)"
	uv run uvicorn backend.main:app --reload & \
	cd frontend && npm run dev

# ── Lint ─────────────────────────────────────────────────────
lint: lint-backend lint-frontend

lint-backend:
	uv run ruff check backend/
	uv run python scripts/lint_rules.py --fail backend/

lint-frontend:
	cd frontend && npm run lint

# ── 格式化 ───────────────────────────────────────────────────
format: format-backend format-frontend

format-backend:
	uv run ruff format backend/

format-frontend:
	cd frontend && npm run format

format-check: format-check-backend format-check-frontend

format-check-backend:
	uv run ruff format --check backend/

format-check-frontend:
	cd frontend && npm run format -- --check

# ── 类型检查 ─────────────────────────────────────────────────
type-check: type-check-backend type-check-frontend

type-check-backend:
	uv run mypy backend/ --no-error-summary

type-check-frontend:
	cd frontend && npm run type-check

# ── 测试 ─────────────────────────────────────────────────────
test: test-backend test-frontend

test-backend:
	uv run pytest

test-frontend:
	cd frontend && npm run test:run

# ── 构建 ─────────────────────────────────────────────────────
build:
	cd frontend && npm run build

# ── 本地质量门 ───────────────────────────────────────────────
check: format-check lint type-check test

# ── 清理 ─────────────────────────────────────────────────────
clean:
	rm -rf frontend/dist
	rm -rf .ruff_cache backend/.ruff_cache
	rm -rf .mypy_cache backend/.mypy_cache
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "==> 清理完成"

# ── Pre-commit ───────────────────────────────────────────────
precommit:
	uv run pre-commit run --all-files
