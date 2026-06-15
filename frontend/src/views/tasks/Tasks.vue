<template>
  <div>
    <ArPageHeader title="托管任务" desc="管理和监控长期运行的后台任务" />
    <ArGrid :cols="2" gap="20px">
      <TaskCard
        title="爬虫管理"
        :icon="BugOutline"
        icon-color="var(--primary-color)"
        :stats="[
          { label: '运行中', value: 3 },
          { label: '今日抓取', value: 12 },
          { label: '累计数据', value: '45K' }
        ]"
        action-text="进入管理 →"
        @click="router.push('/tasks/crawler')"
      />
      <TaskCard
        title="云训练管理"
        :icon="CloudOutline"
        icon-color="#1890ff"
        :stats="[
          { label: '训练中', value: 2 },
          { label: '排队中', value: 5 },
          { label: '平均时长', value: '8h' }
        ]"
        action-text="进入管理 →"
        @click="router.push('/tasks/cloud')"
      />
    </ArGrid>
  </div>
</template>

<script setup lang="ts">
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import ArGrid from '@/components/ui/ArGrid.vue'
import TaskCard from '@/components/widgets/tasks/TaskCard.vue'
import { useRouter } from 'vue-router'
import { BugOutline, CloudOutline } from '@vicons/ionicons5'

const router = useRouter()
</script>
