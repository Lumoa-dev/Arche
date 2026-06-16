# CI/CD Pipeline

## Pipeline Overview

工作流文件按职能拆分，命名用简单英文：

```
.github/workflows/
├── ci.yml               # 编排器 — 按事件调度下游工作流
├── check-lint.yml       # 代码规范检查
├── check-security.yml   # 安全扫描（Bandit + CodeQL）
├── test-unit.yml        # 单元测试（循环扫描全量跑）
├── test-integration.yml # 集成测试 + 攻击测试
├── test-e2e.yml         # 端到端测试（Chrome/Firefox）
├── build.yml            # Docker 构建 + 推送
├── release.yml          # 创建 Release
├── deploy.yml           # SSH 部署
└── pr-labeler.yml       # PR 自动打标签
```

## Pipeline Flow

```
PR:
  check-lint → check-security → test-unit (全量)

Merge to master / Tag v*:
  check-lint → test-integration + test-e2e → build → release + deploy
```

| 阶段 | PR | 合并到 master / Tag v* |
|------|----|----------------------|
| check-lint | ✅ 跑 | ✅ 跑 |
| check-security (Bandit + CodeQL) | ✅ 跑 | ❌ 不跑 |
| test-unit (全量跑) | ✅ 跑 | ❌ 不跑 |
| test-integration (集成+攻击) | ❌ 不跑 | ✅ 跑 |
| test-e2e (Chrome/Firefox) | ❌ 不跑 | ✅ 跑 |
| build + deploy | ❌ 不跑 | ✅ 跑 |

## Trigger Rules

| 触发方式 | 操作 |
|---------|------|
| Tag `v*` | check-lint → test-integration + test-e2e → build → release + deploy |
| 合并 PR 到 `master` | 同上（自动 bump patch 版本） |
| PR (open/sync) | check-lint → check-security → test-unit |
| Push 到 `master`（无 tag） | check-lint + test-integration + test-e2e，不构建 |

## 测试文件说明

| 文件 | 内容 | 执行方式 |
|------|------|---------|
| `test-unit.yml` | 后端每个 plugin 的单元测试 + 前端每个目录的测试 | 循环扫描目录，全量运行 |
| `test-integration.yml` | 后端集成测试 + 攻击测试（原 adversarial） | 两个 job 独立跑 |
| `test-e2e.yml` | Playwright 端到端测试 | 矩阵并行（chromium / firefox） |

定时全量测试（每日 UTC 2:00 = 北京时间 10:00）：
- `test-unit.yml` 定时跑：跑全部 plugin + 前端
- `test-integration.yml` 定时跑：跑集成 + 攻击测试

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

Defined in `.github/workflows/deploy.yml`. Webhook mode：

```
Push to master / tag v* → build image → POST webhook → server pulls + restarts
```

CI 仅发送 HTTP POST 到 `${{ vars.DEPLOY_WEBHOOK_URL }}`，附带 token 和镜像标签。服务器端自行验证 token、拉取镜像、重启服务。不暴露任何 SSH 密钥给 CI。

### 环境变量 / Secrets

| 变量 | 说明 |
|------|------|
| `vars.DEPLOY_WEBHOOK_URL` | 部署端点 URL |
| `secrets.DEPLOY_TOKEN` | 部署令牌，服务器端验证用 |

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
- Bandit 安全扫描：跟随 CodeQL 一同运行
- 攻击测试 (attack test)：master push / 定时 / 手动触发，在 `test-integration.yml` 中运行
- 容器镜像推送至 ghcr.io (非 Docker Hub)
- PyPI 使用阿里云镜像
- 无密钥提交到仓库
