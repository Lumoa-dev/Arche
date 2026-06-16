# Issue 修复工作流（开发模式）

## 场景触发条件
当被安排领取一个或多个 Issue 进行实际代码修复/开发时，需遵循以下工作流。

## 工作流

### 第一步：完整阅读 Issue
- 使用 `gh issue view <number>` 命令读取 Issue 的完整内容（标题、描述、标签、评论）
- 如果 Issue 有评论（Code Review 分析），务必一起阅读，了解已发现的根因和修复方向
- 如果该 Issue 是**子 Issue**，需阅读父 Issue 的上下文

### 第二步：Code Review 验证
- 审查 Issue 涉及的相关代码（后端路由、服务、模型、前端组件、API 调用等）
- 确认问题是否真实存在且可复现
- 确认问题的根因是否与 Issue 描述一致
- 如果发现新的深层问题，在 Issue 下评论补充

### 第三步：确认分支环境
- 运行 `git branch --show-current` 查看当前所在分支
- **如果当前在 `master`、`main`、`develop` 等主分支或开发分支上**：
  - 从当前分支创建新的功能/修复分支
  - 分支命名规范：`fix/issue-<编号>-<简短描述>` 或 `feat/issue-<编号>-<简短描述>`
  - 示例：`fix/issue-85-moderation-api`、`fix/issue-102-alembic-migrations`
- **如果当前已处于非主分支/非开发分支**（如已在功能分支上）：
  - 确认分支用途与当前 Issue 匹配
  - 匹配则直接开始工作
  - 不匹配则按上一条规则创建新分支

### 第四步：代码修复
- 严格按照 Issue 描述和 Code Review 分析进行修复
- 遵循项目现有代码规范和风格
- 修改完成后运行相关 lint 和测试

### 第五步：提交 PR
- 代码修改完成后，提交 Pull Request
- PR 标题格式：`fix: #<编号> <简短描述>` 或 `feat: #<编号> <简短描述>`
- PR 描述中需引用关联的 Issue（使用 `Closes #<编号>` 或 `Ref #<编号>`）
- 确保 CI 通过后再标记为 Ready for Review
