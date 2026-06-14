<script setup lang="ts">
import { h, onMounted, onUnmounted, ref } from 'vue'
import { NTag } from 'naive-ui'
import { ArTable } from '@/components/ui'
import { getProcessesApi, type ProcessInfo } from '@/components/logic/api'
import { SystemMetrics } from '@/components/widgets/admin/SystemMetrics.vue'

const processes = ref<ProcessInfo[]>([])
const loading = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const processColumns = [
  { title: 'PID', key: 'pid', width: 80 },
  { title: '进程名', key: 'name', ellipsis: true },
  {
    title: 'CPU %',
    key: 'cpu_percent',
    width: 120,
    render: (row: ProcessInfo) =>
      h(
        NTag,
        { size: 'small', type: (row.cpu_percent ?? 0) > 50 ? 'error' : 'default' },
        {
          default: () => `${(row.cpu_percent ?? 0).toFixed(1)}%`
        }
      )
  },
  {
    title: '内存 %',
    key: 'memory_percent',
    width: 120,
    render: (row: ProcessInfo) =>
      h(
        NTag,
        { size: 'small', type: (row.memory_percent ?? 0) > 50 ? 'error' : 'default' },
        {
          default: () => `${(row.memory_percent ?? 0).toFixed(1)}%`
        }
      )
  }
]

const fetchProcesses = async () => {
  loading.value = true
  try {
    const res = await getProcessesApi({ limit: 30 }, { silent: true, skipAuthLogout: true })
    if (res) processes.value = res
  } catch {
    // 静默失败，保留上次数据
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchProcesses()
  refreshTimer = setInterval(fetchProcesses, 10000)
})

onUnmounted(() => {
  if (refreshTimer !== null) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<template>
  <div class="system-monitor-page">
    <SystemMetrics />

    <div v-if="processes.length > 0" class="processes-section">
      <h3 class="section-title">进程列表</h3>
      <div class="table-wrapper">
        <ArTable
          :columns="processColumns"
          :data="processes"
          :loading="loading"
          size="small"
          striped
          :bordered="false"
          :single-line="true"
        />
      </div>
    </div>
    <div v-else class="processes-empty">
      <p>暂无进程数据</p>
    </div>
  </div>
</template>

<style scoped>
.system-monitor-page {
  display: flex;
  flex-direction: column;
  gap: var(--layout-gap);
  max-width: 100%;
}

.section-title {
  margin: 0 0 var(--spacing-sm);
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.table-wrapper {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.processes-empty {
  text-align: center;
  padding: 40px 0;
  color: var(--text-tertiary);
}
</style>
