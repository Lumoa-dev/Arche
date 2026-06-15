<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { NProgress, NEmpty } from 'naive-ui'
import { getSystemSummaryApi, type SystemSummary } from '@/components/logic/api'
import { ArCard } from '@/components/ui'

const summary = ref<SystemSummary>({
  cpu_percent: 0,
  memory_percent: 0,
  disk_percent: 0
})
const loading = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const formatBytes = (bytes: number | undefined): string => {
  if (bytes === undefined || bytes === null) return '-'
  if (bytes < 1024) return `${bytes.toFixed(1)} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

const formatRate = (bytes: number | undefined): string => {
  if (bytes === undefined || bytes === null) return '-'
  return `${formatBytes(bytes)}/s`
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getSystemSummaryApi({ silent: true, skipAuthLogout: true })
    if (res) summary.value = res
  } catch {
    // 静默失败，保留上次数据
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
  refreshTimer = setInterval(fetchData, 10000)
})

onUnmounted(() => {
  if (refreshTimer !== null) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<template>
  <div class="system-metrics">
    <div v-if="loading && !summary.cpu_percent && !summary.memory_percent" class="empty-state">
      <NEmpty description="加载中..." />
    </div>
    <div v-else class="metrics-grid">
      <!-- CPU -->
      <ArCard class="metric-card">
        <div class="metric-body">
          <div class="metric-label">CPU 使用率</div>
          <NProgress
            type="line"
            :percentage="Math.round(summary.cpu_percent ?? 0)"
            :color="summary.cpu_percent && summary.cpu_percent > 80 ? '#c23a2b' : '#9a5a2f'"
            :rail-color="'rgba(26, 24, 23, 0.08)'"
            :height="10"
            :border-radius="5"
            :fill-border-radius="5"
            indicator-placement="inside"
            class="metric-progress"
          />
          <div class="metric-value">
            <span class="metric-number">{{ Math.round(summary.cpu_percent ?? 0) }}%</span>
            <span v-if="summary.cpu_count" class="metric-sub">({{ summary.cpu_count }} 核)</span>
          </div>
          <div class="metric-detail">
            <span
              >负载：{{ summary.load_1?.toFixed(2) ?? '-' }} /
              {{ summary.load_5?.toFixed(2) ?? '-' }}</span
            >
          </div>
        </div>
      </ArCard>

      <!-- 内存 -->
      <ArCard class="metric-card">
        <div class="metric-body">
          <div class="metric-label">内存使用率</div>
          <NProgress
            type="line"
            :percentage="Math.round(summary.memory_percent ?? 0)"
            :color="summary.memory_percent && summary.memory_percent > 80 ? '#c23a2b' : '#b8743d'"
            :rail-color="'rgba(26, 24, 23, 0.08)'"
            :height="10"
            :border-radius="5"
            :fill-border-radius="5"
            indicator-placement="inside"
            class="metric-progress"
          />
          <div class="metric-value">
            <span class="metric-number">{{ Math.round(summary.memory_percent ?? 0) }}%</span>
            <span class="metric-sub">
              ({{ summary.memory_used_gb?.toFixed(1) ?? '-' }} /
              {{ summary.memory_total_gb?.toFixed(1) ?? '-' }} GB)
            </span>
          </div>
        </div>
      </ArCard>

      <!-- 磁盘 -->
      <ArCard class="metric-card">
        <div class="metric-body">
          <div class="metric-label">磁盘使用率</div>
          <NProgress
            type="line"
            :percentage="Math.round(summary.disk_percent ?? 0)"
            :color="summary.disk_percent && summary.disk_percent > 80 ? '#c23a2b' : '#6f3f22'"
            :rail-color="'rgba(26, 24, 23, 0.08)'"
            :height="10"
            :border-radius="5"
            :fill-border-radius="5"
            indicator-placement="inside"
            class="metric-progress"
          />
          <div class="metric-value">
            <span class="metric-number">{{ Math.round(summary.disk_percent ?? 0) }}%</span>
            <span class="metric-sub">
              ({{ summary.disk_used_gb?.toFixed(1) ?? '-' }} /
              {{ summary.disk_total_gb?.toFixed(1) ?? '-' }} GB)
            </span>
          </div>
        </div>
      </ArCard>

      <!-- 网络 -->
      <ArCard class="metric-card">
        <div class="metric-body">
          <div class="metric-label">网络</div>
          <div class="network-stats">
            <div class="network-row">
              <span class="network-dir">发送</span>
              <span class="network-value">{{ formatRate(summary.net_sent) }}</span>
            </div>
            <div class="network-row">
              <span class="network-dir">接收</span>
              <span class="network-value">{{ formatRate(summary.net_recv) }}</span>
            </div>
          </div>
          <div v-if="summary.process_count !== undefined" class="metric-detail">
            <span>进程数：{{ summary.process_count }}</span>
            <span v-if="summary.uptime">运行时间：{{ Math.round(summary.uptime / 3600) }}h</span>
          </div>
        </div>
      </ArCard>
    </div>
  </div>
</template>

<style scoped>
.system-metrics {
  width: 100%;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-card {
  width: 100%;
}

.metric-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.metric-value {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-tertiary);
}

.metric-number {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.metric-sub {
  font-size: 12px;
  color: var(--text-tertiary);
}

.metric-detail {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-tertiary);
  padding-top: 4px;
  border-top: 1px solid var(--border-color);
}

.network-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.network-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.network-dir {
  color: var(--text-secondary);
  font-weight: 500;
}

.network-value {
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
  font-weight: 600;
}
</style>
