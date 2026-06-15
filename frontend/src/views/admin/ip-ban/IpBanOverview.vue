<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { BanOutline, TimeOutline, SettingsOutline } from '@vicons/ionicons5'
import ArGrid from '@/components/ui/ArGrid.vue'
import OverviewCard from '@/components/widgets/admin/OverviewCard.vue'
import { getIpBanStatsApi } from '@/lib/services/api/ipBan'
import type { IpBanStats } from '@/lib/services/api/ipBan'

const stats = ref<IpBanStats>({
  total_bans: 0,
  active_bans: 0,
  auto_bans: 0,
  manual_bans: 0,
  today_bans: 0
})

onMounted(async () => {
  try {
    stats.value = await getIpBanStatsApi()
  } catch {
    // 静默处理
  }
})

const cards = computed(() => [
  {
    title: '封禁列表',
    icon: BanOutline,
    stats: [
      { label: '总计封禁', value: stats.value.total_bans },
      { label: '活跃封禁', value: stats.value.active_bans },
      { label: '今日新增', value: stats.value.today_bans }
    ],
    to: '/admin/ops/ip-ban/list'
  },
  {
    title: '操作日志',
    icon: TimeOutline,
    stats: [{ label: '封禁/解封', value: '查看全部' }],
    to: '/admin/ops/ip-ban/logs'
  },
  {
    title: '自动封禁规则',
    icon: SettingsOutline,
    stats: [
      { label: '规则数量', value: 4 },
      { label: '登录失败', value: '30分钟' },
      { label: '高频4xx', value: '1小时' }
    ],
    to: '/admin/ops/ip-ban/rules'
  }
])
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
    />
  </ArGrid>
</template>
