<script setup lang="ts">
import {
  PulseOutline,
  SettingsOutline,
  CloudOutline,
  BanOutline,
  ShieldCheckmarkOutline,
  ExtensionPuzzleOutline,
  ServerOutline
} from '@vicons/ionicons5'
import OverviewCard from '@/components/widgets/admin/OverviewCard.vue'
import ArGrid from '@/components/ui/ArGrid.vue'

const cards = [
  {
    title: '系统监控',
    icon: PulseOutline,
    stats: [
      { label: 'CPU', value: '23%' },
      { label: '内存', value: '45%' },
      { label: '磁盘', value: '67%' }
    ],
    to: '/admin/ops/system'
  },
  {
    title: '运行时配置',
    icon: SettingsOutline,
    stats: [
      { label: '已配置', value: '12 项' },
      { label: '系统默认', value: '8 项' }
    ],
    to: '/admin/ops/config'
  },
  {
    title: 'OSS 存储管理',
    icon: CloudOutline,
    stats: [
      { label: '总存储', value: '2.1 TB' },
      { label: '已用', value: '1.2 TB' },
      { label: '用户', value: '128 人' }
    ],
    to: '/admin/ops/storage'
  },
  {
    title: 'IP 封禁管理',
    icon: BanOutline,
    stats: [
      { label: '封禁列表', value: '管理' },
      { label: '自动规则', value: '配置' },
      { label: '操作日志', value: '查看' }
    ],
    to: '/admin/ops/ip-ban'
  },
  {
    title: '权限管理',
    icon: ShieldCheckmarkOutline,
    stats: [
      { label: '等级', value: 'P0~P5' },
      { label: '权限规则', value: '24 条' }
    ],
    disabled: true,
    note: '暂无'
  },
  {
    title: '插件管理',
    icon: ExtensionPuzzleOutline,
    stats: [
      { label: '已安装', value: 8 },
      { label: '已启用', value: 6 }
    ],
    disabled: true,
    note: '暂未实现'
  },
  {
    title: '日志管理',
    icon: ServerOutline,
    stats: [
      { label: '今日日志', value: '234 条' },
      { label: '错误', value: '3 条' }
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
