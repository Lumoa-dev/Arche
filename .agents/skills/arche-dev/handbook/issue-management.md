# Issue 管理规范

## 标签体系

所有 Issue 必须使用以下标准化标签体系：

### Type（必选其一）

| 标签 | 颜色 | 说明 |
|------|------|------|
| `type: bug` | `d73a4a` | 功能缺陷 |
| `type: feature` | `a2eeef` | 新功能/新页面 |
| `type: enhancement` | `a2eeef` | 对现有功能的优化 |
| `type: ui` | `d4c5f9` | 样式/显示问题 |
| `type: refactor` | `fbca04` | 代码重构 |
| `type: docs` | `7057ff` | 文档变更 |
| `type: chore` | `bfdadc` | 杂项（配置、脚本、依赖等） |

### Area（可选，可多选）

| 标签 | 颜色 | 说明 |
|------|------|------|
| `area: backend` | `000000` | 后端 |
| `area: frontend` | `1d76db` | 前端 |
| `area: ci-cd` | `5319e7` | CI/CD |

### Priority（可选）

| 标签 | 颜色 | 说明 |
|------|------|------|
| `priority: high` | `e11d21` | 阻塞性，优先处理 |
| `priority: medium` | `eb6420` | 正常排期 |
| `priority: low` | `009800` | 低优先级/备选 |

### 其他（可选）

| 标签 | 颜色 | 说明 |
|------|------|------|
| `good first issue` | `7057ff` | 新手友好 |
| `help wanted` | `008672` | 需要帮助 |
| `heavy` | `000000` | 重型任务，需专门规划 |
| `question` | `d876e3` | 疑问/讨论 |
| `needs-info` | `f9d71c` | 信息不完整，需要补充 |
| `duplicate` | `cfd3d7` | 重复 Issue |
| `invalid` | `e4e669` | 无效 Issue |
| `stale` | `ffffff` | 长期未活动 |

标签定义源文件：[`.github/labels.json`](file:///d:/Project/Arche/.github/labels.json)，通过 CI 自动同步到仓库。

---

## Issue 模板

项目提供四个 Issue 模板，位于 `.github/ISSUE_TEMPLATE/`：

| 模板 | 文件名 | 默认 labels | 适用场景 |
|------|--------|------------|---------|
| Bug 报告 | `bug_report.md` | `type: bug` | 功能缺陷报告 |
| 功能建议 | `feature_request.md` | `type: feature` | 新功能/新页面建议 |
| 任务/代办 | `custom.md` | 无默认 | 具体的开发任务、待办事项 |
| Epic 任务汇总 | `epic.md` | 无默认 | 创建 Epic 总览，聚合一组子任务 |

创建 Issue 时选择对应模板，模板中已包含建议标签选项和填写指引。

> **设计原则**：模板数量控制在 4 个，覆盖所有场景而不冗余。Bug、Feature、Task 是三种核心类型，Epic 是特殊的聚合类型。不需要为每个 type 标签各自建一个模板（如 `type: ui` 问题用 Bug 或 Task 模板即可，通过标签区分）。

---

## Epic + Sub-issue 架构

项目使用 GitHub Sub-issues 特性管理大型任务：

```
Epic Issue（父级）
├── Sub-issue 1（具体任务）
├── Sub-issue 2（具体任务）
└── Sub-issue 3（具体任务）
```

### Epic 规范

- **标题格式**: `[Epic] <类别名称>`，不使用 emoji
- **Body 格式**:

```markdown
## 概述

[一句话说明本 Epic 覆盖范围]

## 子任务

### 分类名

- [ ] #<编号> 子任务标题
```

- Epic body 中的 checklist 项必须对应实际存在的 Issue 编号
- 每个 checklist 项使用 `- [ ] #123 标题` 格式，通过 GraphQL API 建立 sub-issue 关系

### Sub-issue 规范

- 每个子 Issue 只能有一个父 Issue（GitHub 限制）
- 子 Issue 使用标准的标签体系
- 子 Issue 标题应简洁明了，能独立表达任务内容

---

## Issue 创建流程

### AI 辅助创建时的标准化流程

当需要创建 Issue 时，按以下步骤操作：

```
1. 明确分类
   - Bug → type: bug
   - 新功能/页面 → type: feature
   - 优化现有功能 → type: enhancement
   - 样式问题 → type: ui
   - 其他 → type: chore / refactor / docs

2. 确定归属
   - 是否属于某个已有 Epic？
   - 如果属于，在 Epic body 中追加 checklist 项
   - 如果不属于，作为独立 Issue 创建

3. 创建 Issue 本体
   - 使用对应模板
   - 填写完整的标题和描述
   - 打上正确的 type / area / priority 标签

4. 建立关联（如适用）
   - 如果是现有 Epic 的子任务：
     a. 更新 Epic body 追加 checklist 项
     b. 通过 GraphQL API 建立 sub-issue 关系：
        ```bash
        gh api graphql -f query='
          mutation {
            addSubIssue(input: {issueId: "<epic_node_id>", subIssueId: "<child_node_id>"}) {
              subIssue { id }
            }
          }
        '
        ```

5. 最终检查
   - 标签是否完整且正确
   - 父子关系是否已建立（如需）
   - 标题是否简洁明了
```

### 获取 Node ID

Sub-issue 关系需要通过 GraphQL API 建立，需要先获取 Issue 的 Node ID：

```bash
# 获取单个 Issue 的 Node ID
gh api graphql -f query='query {
  repository(owner: "Lumoa-dev", name: "Arche") {
    issue(number: <ISSUE_NUMBER>) { id }
  }
}'

# 批量获取
gh api graphql -f query='
query {
  issue1: repository(owner: "Lumoa-dev", name: "Arche") { issue(number: <N1>) { id } }
  issue2: repository(owner: "Lumoa-dev", name: "Arche") { issue(number: <N2>) { id } }
}'
```

---

## Issue 管理工作流

### 纯决策模式（不涉及代码修改）

1. **Code Review 验证**: 拉取 Issue 详细信息，审查相关代码，确认问题本质
2. **分类处理**:
   - 问题不存在/已修复 → 关闭 Issue，评论说明
   - 问题存在但发现更深层次问题 → 评论补充完整分析报告
   - 复合问题 → 拆分为多个子 Issue
3. **工具使用**: 用 `gh` CLI 操作（close / comment / create），用 Code Review 工具审查代码

### 开发修复模式

参考 [issue-fix-workflow.md](file:///d:/Project/Arche/.trae/rules/issue-fix-workflow.md)：
1. 完整阅读 Issue（含评论中的 Code Review 分析）
2. 确认分支环境，从主分支创建 `fix/issue-<编号>-<描述>` 分支
3. 按 Issue 描述和 Code Review 分析进行修复
4. 提交 PR，标题格式 `fix: #<编号> <描述>`

---

## PR 模板

项目提供单个 PR 模板 `.github/PULL_REQUEST_TEMPLATE.md`，包含：

- **摘要** — 建议按 Conventional Commits 格式填写
- **关联 Issue** — 使用 `Closes / Fixes / Ref` 关键词
- **变更类型** — 勾选变更类别
- **自测清单** — 涵盖 lint、test、type-check、API 类型同步
- **测试步骤** — 给 reviewer 的验证指引
- **截图** — UI 变更必填

> GitHub 支持多个 PR 模板（通过 `PULL_REQUEST_TEMPLATE/` 目录），但对于本项目规模，单个模板足够覆盖所有 PR 场景。不同类型的变更通过标签和关联 Issue 区分即可。

## 安全策略

安全问题通过 [`.github/SECURITY.md`](file:///d:/Project/Arche/.github/SECURITY.md) 说明，核心要点：
- 通过 Issue 提交（标题加 `[Security]` 前缀）
- 不要公开披露漏洞细节
- 48 小时内确认收到

## 标签同步

标签定义在 [`.github/labels.json`](file:///d:/Project/Arche/.github/labels.json)，通过 [`.github/workflows/label-sync.yml`](file:///d:/Project/Arche/.github/workflows/label-sync.yml) 每周一自动同步到 GitHub 仓库。

如需新增或修改标签：
1. 编辑 `labels.json`
2. 等待 label-sync 工作流自动执行
3. 或手动触发：`gh workflow run label-sync.yml`
