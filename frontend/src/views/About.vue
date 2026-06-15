<template>
  <ArPage>
    <ArCard variant="elevated" padding="3xl" style="width: min(900px, 100%); margin: 0 auto; line-height: var(--line-height-relaxed);">
      <p style="margin: 0; color: var(--text-tertiary); font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase;">关于锦年志</p>
      <h1 style="margin: var(--spacing-sm) 0 var(--spacing-md); font-size: 30px; color: var(--text-primary);">记录时光，分享成长</h1>
      <p style="margin: 0 0 var(--spacing-md); color: var(--text-secondary);">
        锦年志是一个面向对外展示的日志空间。我们用文字记录风华正茂的阶段，也欢迎更多创作者在这里一起共创、交流与沉淀。
      </p>
      <p style="margin: 0 0 var(--spacing-md); color: var(--text-secondary);">
        这里不追求短期商业收益，更重视内容质量、创作氛围和长期价值。每一篇日志都是当下的痕迹，也是未来回看的线索。
      </p>
    </ArCard>
  </ArPage>
</template>

<script setup lang="ts">
import ArPage from '@/components/ui/ArPage.vue'
import ArCard from '@/components/ui/ArCard.vue'
</script>
