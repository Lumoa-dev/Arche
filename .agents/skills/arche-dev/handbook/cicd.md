# CI/CD Pipeline

## Pipeline Overview

工作流文件按职能拆分，命名用简单英文：

```
.github/workflows/
├── ci.yml               # 编排器 — 按事件调度下游工作流
├── check-lint.yml       # 代码规范检查
├── check-security.yml   # 安全扫描（Bandit + CodeQL）
├── test-unit.yml        # 单元测试（矩阵并行）
├── test-integration.yml # 集成测试 + 攻击测试
├── test-e2e.yml         # 端到端测试（Chrome/Firefox）
├── build.yml            # Docker 构建 + 推送
├── deploy.yml           # 部署到服务器
├── release.yml          # 创建 Release
├── label-sync.yml       # 标签同步
└── pr-labeler.yml       # PR 自动打标签
```

## Pipeline Flow

```
PR:
  check-lint → check-security → test-unit (按改动目录并行)

Merge to master / Tag v*:
  check-lint → test-integration + test-e2e → build → release + deploy
```

| 阶段 | PR | 合并到 master / Tag v* |
|------|----|----------------------|
| check-lint | ✅ 跑 | ✅ 跑 |
| check-security (Bandit + CodeQL) | ✅ 跑 | ❌ 不跑 |
| test-unit (按变更目录矩阵) | ✅ 跑 | ❌ 不跑 |
| test-integration (集成+攻击) | ❌ 不跑 | ✅ 跑 |
| test-e2e (Chrome/Firefox) | ❌ 不跑 | ✅ 跑 |
| build + deploy | ❌ 不跑 | ✅ 跑 |
| 失败告警 | — | ✅ 集成/攻击失败时自动建 Issue + fix 分支 |

## Trigger Rules

| 触发方式 | 操作 |
|---------|------|
| Tag `v*` | check-lint → test-integration + test-e2e → build → release + deploy |
| 合并 PR 到 `master` | 同上（自动 bump patch 版本） |
| PR (open/sync) | check-lint → check-security → test-unit（按改动目录） |
| Push 到 `master`（无 tag） | check-lint + test-integration + test-e2e，不构建 |

## 测试文件说明

| 文件 | 内容 | 并行方式 |
|------|------|---------|
| `test-unit.yml` | 后端每个 plugin 的单元测试 + 前端每个目录的测试，按改动目录筛选 | 矩阵并行（每个 plugin/目录一个 job） |
| `test-integration.yml` | 后端集成测试 + 攻击测试（原 adversarial） | 顺序（两个 job 独立跑） |
| `test-e2e.yml` | Playwright 端到端测试 | 矩阵并行（chromium / firefox） |

定时全量测试（每日 UTC 2:00 = 北京时间 10:00）：
- `test-unit.yml` 定时跑：跑全部 plugin + 前端 + 覆盖率报告
- `test-integration.yml` 定时跑：跑集成 + 攻击测试

## 失败处理机制

当 master 上的集成测试或攻击测试失败时：

1. **停止构建**：`build` job 通过 `needs` 依赖 `test-integration` 和 `test-e2e`，失败时自动跳过
2. **自动建 Issue**：`alert-fail` job 创建名为 `集成/攻击测试失败 (yyyy-mm-dd)` 的 Issue，标签 `bug` + `auto-generated`
3. **自动建 fix 分支**：基于失败时的 commit 创建 `fix/integration-failure-yyyy-mm-dd` 分支并推送

## Build

Defined in `.github/workflows/build.yml`. Builds Docker image and pushes to GitHub Container Registry:

```
ghcr.io/<org>/arche:<version>
```

### Docker Compose (Production)

```
docker-compose.yml
├── nginx (reverse proxy + SSL)
├── backend
├── postgresql
└── minio
```

## Versioning

- Automatic patch version bump on PR merge to master
- Tags follow semver: `v1.2.3`
- `tag-release` job auto-creates and pushes tags on successful master builds

## Deployment

Defined in `.github/workflows/deploy.yml`. Production serves via Nginx reverse proxy.

### Environment Variables

- `.env` file for local dev
- Environment variables for CI/production
- Database config for production settings

## API Type Sync

```bash
cd frontend && npm run generate:api
# → fetches OpenAPI schema from running backend
# → generates src/services/api/generated.d.ts
```

CI verifies that the generated types file exists and is up-to-date:
```bash
test -f src/services/api/generated.d.ts
```

## Security

- CodeQL 安全扫描：仅 PR + 手动触发时运行（master 不跑）
- Bandit 安全扫描：跟随 CodeQL 一同运行，仅当有 Python 变更时触发
- 攻击测试 (attack test)：master push / 定时 / 手动触发，在 `test-integration.yml` 中运行
- 容器镜像推送至 ghcr.io (非 Docker Hub)
- PyPI 使用阿里云镜像
- 无密钥提交到仓库
