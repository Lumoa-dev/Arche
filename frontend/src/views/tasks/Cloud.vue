<template>
  <div>
    <ArPageHeader title="云训练管理" desc="管理和监控云端模型训练任务" />
    <ArGrid columns="1fr 1fr" gap="20px" style="margin-bottom: 20px;">
      <TaskCard
        title="训练概览"
        :icon="CloudOutline"
        iconColor="#1890ff"
        :stats="[{label:'训练中',value:2},{label:'排队中',value:5},{label:'平均时长',value:'8h'}]"
      />
    </ArGrid>
    <ArCard variant="elevated" padding="3xl" style="text-align: center; color: var(--text-tertiary);">
      <ArVBox gap="var(--spacing-md)" align="center">
        <p>云训练任务详情功能开发中，敬请期待</p>
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
import { CloudOutline } from '@vicons/ionicons5'
</script>
