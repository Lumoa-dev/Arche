<script setup lang="ts">
import { DocumentTextOutline, ChatbubblesOutline, WarningOutline } from '@vicons/ionicons5'
import OverviewCard from '@/components/widgets/admin/OverviewCard.vue'
import ArGrid from '@/components/ui/ArGrid.vue'

const cards = [
  {
    title: '帖子审核',
    icon: DocumentTextOutline,
    stats: [
      { label: '待审核', value: 7 },
      { label: '今日通过', value: 12 },
      { label: '今日驳回', value: 3 }
    ],
    to: '/admin/content/moderation'
  },
  {
    title: '评论管理',
    icon: ChatbubblesOutline,
    stats: [
      { label: '待审核评论', value: 5 },
      { label: '举报待处理', value: 2 }
    ],
    disabled: true,
    note: '暂未实现'
  },
  {
    title: '举报处理',
    icon: WarningOutline,
    stats: [
      { label: '待处理举报', value: 2 },
      { label: '今日新增', value: 1 }
    ],
    disabled: true,
    note: '暂未实现'
  }
]
</script>

<template>
  <ArGrid columns="1fr 1fr 1fr" gap="var(--spacing-md)">
    <OverviewCard
      v-for="card in cards"
      :key="card.title"
      :title="card.title"
      :icon="card.icon"
      :stats="card.stats"
      :to="card.to"
      :disabled="card.disabled"
      :note="card.note"
    />
  </ArGrid>
</template>
