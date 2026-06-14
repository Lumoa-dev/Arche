// 业务组件 — 基于 Ar 设计系统构建的复合组件
// 按功能域划分子目录，统一通过此文件导出

// ── 博客业务 ──
export { default as HeroCarousel } from './common/HeroCarousel.vue'
export { default as PostDetail } from './blog/PostDetail.vue'
export { default as PostEditor } from './blog/PostEditor.vue'
export { default as CoverUploader } from './blog/CoverUploader.vue'
export { default as AssetSidebar } from './blog/AssetSidebar.vue'
export { default as LikeButton } from './common/LikeButton.vue'
export { default as FavoriteButton } from './common/FavoriteButton.vue'
export { default as ShareButton } from './common/ShareButton.vue'
export { default as AuthorBar } from './blog/AuthorBar.vue'
export { default as TrendingTags } from './blog/TrendingTags.vue'
export { default as WatchHistoryStack } from './blog/WatchHistoryStack.vue'
export { default as ParagraphComponent } from './blog/ParagraphComponent.vue'
export { default as PostTitle } from './blog/PostTitle.vue'
export { default as PostIntro } from './blog/PostIntro.vue'

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
