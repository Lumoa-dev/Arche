---
alwaysApply: true
scene: git_message
---

# Git Commit Message 规范

基于 [Conventional Commits](https://www.conventionalcommits.org/) 标准，结合项目实际提交历史整理。

## 格式

```
<type>(<scope>): <description>

[可选的 body，补充说明 WHY]
```

- 总长度不超过 72 字符（含 type 和 scope）
- type 和 scope 之间不加空格
- `:` 后加一个空格
- scope 可选，不加 scope 时直接 `<type>: <description>`

## Type（必选）

| Type | 说明 | 使用场景 |
|------|------|----------|
| `feat` | 新功能 | 新增功能特性、新的组件、新的 API 端点等 |
| `fix` | Bug 修复 | 修复 Bug、解决运行时错误、修复类型错误等 |
| `refactor` | 重构 | 代码重构、组件重写、优化结构，不改变外部行为 |
| `test` | 测试相关 | 新增测试用例、修改测试、测试基础设施变更 |
| `ci` | CI/CD | GitHub Actions 工作流、构建配置、部署脚本等 |
| `chore` | 杂项 | 构建工具、依赖管理、配置文件、删除废弃代码等 |
| `style` | 代码格式 | 格式化、代码风格调整（ruff format、prettier 等），不涉及逻辑变更 |
| `docs` | 文档 | 仅文档变更，不涉及代码 |
| `perf` | 性能优化 | 性能优化（暂未在项目中使用，作为预留） |

## Scope（可选）

scope 标识变更的作用域，使用 **小写 kebab-case**：

### 后端 scope

- `core` — 核心框架变更
- `models` — 数据模型变更
- `auth` — 认证/授权
- `blog` — 博客功能
- `admin` — 后台管理
- `config` — 配置管理
- `plugins` — 插件系统
- `oss` — 对象存储
- `monitor` — 系统监控
- `ci` — CI/CD 配置

### 前端 scope

- `frontend` — 前端通用/跨模块变更
- `ui` — UI 组件库（ArButton, ArCard, ArTable 等）
- `blog` — 博客前端组件
- `admin` — 管理后台前端
- `user` — 用户相关前端
- `router` — 路由配置
- `api` — API 调用层

### 其他 scope

- `deps` — 依赖变更
- `scripts` — 工具脚本
- `gitignore` — .gitignore 相关
- `docker` — Docker 配置

> 如果 scope 不确定或变更涉及多个模块，可以不写 scope。

## Description（必选）

- 使用**中文**描述（项目惯例）
- 祈使句，简洁明了，说明"做了什么"而非"为什么做"
- 首字母**不大写**，末尾**不加句号**
- Issue 修复在描述中包含 `#<编号>` 引用

### 示例

```
feat(blog): 新增标签云组件和热门文章列表
fix(auth): 修复 token 刷新时并发请求导致 401 的问题
refactor(frontend): 统一替换硬编码色值为 CSS 变量
test(blog): 新增 PostCard 组件单元测试
ci: 升级 setup-uv 到 v8.0.0 版本
chore: 删除废弃的测试生成工具和种子数据脚本
style: 应用 ruff format 格式化后端代码
docs(readme): 补充环境变量配置说明
fix: #84 修复配置管理页面无种子数据问题
```

## 多行 Commit

当变更需要补充 WHY 时使用多行：

```
feat(blog): 新增自动封面生成功能

自动从文章首段提取文本，使用 Canvas 生成图片封面。
当未手动设置封面时自动使用此功能。
```

## 与 Issue 关联

- 修复 Issue：在 description 中引用 `fix: #<编号> 修复xxx`
- 关联 Issue（非修复）：在 body 中使用 `Ref #<编号>`
- 关闭 Issue：PR 描述中使用 `Closes #<编号>`

## 禁止的模式

- ❌ 使用 emoji（如 `:bug: fix xxx`）
- ❌ description 以大写字母开头（如 `Fix xxx`）
- ❌ description 末尾加句号
- ❌ 使用 `feat:` 写纯英文描述（项目约定以中文为主）
- ❌ 提交信息过长（超 72 字符）
