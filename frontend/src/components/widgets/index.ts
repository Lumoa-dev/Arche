// 业务组件 — 基于 Ar 设计系统构建的复合组件
// 按功能域划分子目录，统一通过此文件导出

// ── 博客业务 ──
export { default as PostCard } from './blog/PostCard.vue'
export { default as HeroCarousel } from './blog/HeroCarousel.vue'
export { default as PostDetail } from './blog/PostDetail.vue'
export { default as PostEditor } from './blog/PostEditor.vue'
export { default as RichTextEditor } from './blog/RichTextEditor.vue'
export { default as CoverUploader } from './blog/CoverUploader.vue'
export { default as AssetSidebar } from './blog/AssetSidebar.vue'
export { default as LikeButton } from './blog/LikeButton.vue'
export { default as FavoriteButton } from './blog/FavoriteButton.vue'
export { default as ShareButton } from './blog/ShareButton.vue'
export { default as CommentList } from './blog/CommentList.vue'
export { default as CommentForm } from './blog/CommentForm.vue'
export { default as TagList } from './blog/TagList.vue'
export { default as AuthorBar } from './blog/AuthorBar.vue'
export { default as FloatingActions } from './blog/FloatingActions.vue'
export { default as TrendingTags } from './blog/TrendingTags.vue'
export { default as WatchHistoryStack } from './blog/WatchHistoryStack.vue'
export { default as ParagraphCommentPanel } from './blog/ParagraphCommentPanel.vue'
export { default as ParagraphComponent } from './blog/ParagraphComponent.vue'

// ── 管理后台 ──
export { default as ModerationPanel } from './admin/ModerationPanel.vue'
export { default as PostTable } from './admin/PostTable.vue'
export { default as UserTable } from './admin/UserTable.vue'
export { default as SystemMetrics } from './admin/SystemMetrics.vue'

// ── 用户相关 ──
export { default as UserCard } from './user/UserCard.vue'
export { default as UserMenu } from './user/UserMenu.vue'
export type { MenuItem } from './user/UserMenu.vue'

// --- 通用业务 ──
export { default as ConsoleShell } from './common/ConsoleShell.vue'
export { default as SiteLogo } from './common/SiteLogo.vue'
