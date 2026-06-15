<template>
  <div>
    <ArPageHeader title="爬虫管理" desc="管理和监控爬虫任务的运行状态" />
    <ArGrid columns="1fr 1fr" gap="20px" style="margin-bottom: 20px">
      <TaskCard
        title="爬虫概览"
        :icon="BugOutline"
        icon-color="var(--primary-color)"
        :stats="[
          { label: '运行中', value: 3 },
          { label: '今日抓取', value: 12 },
          { label: '累计数据', value: '45K' }
        ]"
      />
    </ArGrid>
    <ArCard variant="elevated" padding="lg" style="text-align: center; color: var(--text-tertiary)">
      <ArVBox gap="var(--spacing-md)" align="center">
        <p>爬虫任务详情功能开发中，敬请期待</p>
        <BackButton to="/tasks" />
      </ArVBox>
    </ArCard>
  </div>
</template>

<script setup lang="ts">
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import ArGrid from '@/components/ui/ArGrid.vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import TaskCard from '@/components/widgets/tasks/TaskCard.vue'
import BackButton from '@/components/widgets/tasks/BackButton.vue'
import { BugOutline } from '@vicons/ionicons5'
</script>
