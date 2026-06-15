// 组件逻辑层 — 存放业务组件专用的组合式函数和 API 调用封装
// 与 src/composables/（全局通用逻辑）不同，此目录存放特定于 widgets/ 组件的逻辑
//
// 文件组织建议：
//   usePostActions.ts      — 帖子交互逻辑（点赞、收藏、分享）
//   useCommentSystem.ts    — 评论系统逻辑
//   usePostEditor.ts       — 编辑器逻辑
//   useModeration.ts       — 审核管理逻辑
//   useUserProfile.ts      — 用户资料逻辑
//   api/                   — 业务组件专用的 API 调用封装
