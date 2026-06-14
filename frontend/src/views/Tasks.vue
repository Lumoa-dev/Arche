<template>
  <div class="tasks-page">
    <ArPageHeader title="托管任务" desc="管理和监控长期运行的后台任务" />
    <div class="card-grid">
      <!-- 爬虫管理卡片 -->
      <div class="card" @click="router.push('/tasks/crawler')">
        <div class="card-header">
          <NIcon size="28" class="card-icon crawler-icon"><BugOutline /></NIcon>
          <span class="card-title">爬虫管理</span>
        </div>
        <div class="card-stats">
          <div class="stat-item">
            <span class="stat-value">3</span>
            <span class="stat-label">运行中</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">12</span>
            <span class="stat-label">今日抓取</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">45K</span>
            <span class="stat-label">累计数据</span>
          </div>
        </div>
        <button class="card-action">进入管理 →</button>
      </div>

      <!-- 云训练管理卡片 -->
      <div class="card" @click="router.push('/tasks/cloud')">
        <div class="card-header">
          <NIcon size="28" class="card-icon cloud-icon"><CloudOutline /></NIcon>
          <span class="card-title">云训练管理</span>
        </div>
        <div class="card-stats">
          <div class="stat-item">
            <span class="stat-value">2</span>
            <span class="stat-label">训练中</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">5</span>
            <span class="stat-label">排队中</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">8h</span>
            <span class="stat-label">平均时长</span>
          </div>
        </div>
        <button class="card-action">进入管理 →</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import { BugOutline, CloudOutline } from '@vicons/ionicons5'

const router = useRouter()
</script>

<style scoped>
.tasks-page {
  max-width: 100%;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.card-icon {
  padding: 10px;
  border-radius: var(--radius-sm);
}

.crawler-icon {
  background: rgba(154, 90, 47, 0.1);
  color: var(--primary-color);
}

.cloud-icon {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.card-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.card-action {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.card-action:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
}
</style>
