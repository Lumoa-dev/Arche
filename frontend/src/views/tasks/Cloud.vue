<template>
  <div class="page-shell">
    <ArPageHeader title="云训练管理" desc="管理和监控云端模型训练任务" />
    <div class="card-grid">
      <div class="card">
        <div class="card-header">
          <NIcon size="28" class="card-icon cloud-icon"><CloudOutline /></NIcon>
          <span class="card-title">训练概览</span>
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
      </div>
    </div>
    <div class="placeholder-card">
      <p>云训练任务详情功能开发中，敬请期待</p>
      <button class="back-link" @click="router.push('/tasks')">← 返回任务中心</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import { CloudOutline } from '@vicons/ionicons5'

const router = useRouter()
</script>

<style scoped>
.page-shell {
  max-width: 100%;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  transition: all 0.2s ease;
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

.placeholder-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-3xl);
  text-align: center;
  color: var(--text-tertiary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
}

.back-link {
  padding: 8px 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.2s ease;
}

.back-link:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
}
</style>
