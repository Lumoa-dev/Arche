<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ArTable from '@/components/ui/ArTable.vue'
import ArPagination from '@/components/ui/ArPagination.vue'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import ArTag from '@/components/ui/ArTag.vue'
import ArButton from '@/components/ui/ArButton.vue'
import { getBanLogsApi, type IpBanLogRecord } from '@/lib/services/api/ipBan'

const logs = ref<IpBanLogRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

async function loadLogs() {
  loading.value = true
  try {
    const result = await getBanLogsApi({ page: page.value, page_size: pageSize.value })
    logs.value = result.list
    total.value = result.total
  } catch {
    // 静默处理
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)

const columns = [
  { key: 'ip_or_cidr', title: 'IP/CIDR' },
  { key: 'action', title: '操作' },
  { key: 'ban_type', title: '类型' },
  { key: 'reason', title: '原因' },
  { key: 'operator', title: '操作人' },
  { key: 'detail', title: '详情' },
  { key: 'created_at', title: '时间' }
]
</script>

<template>
  <div>
    <ArPageHeader title="封禁操作日志" description="IP 封禁和解封的历史操作记录">
      <ArButton @click="loadLogs">刷新</ArButton>
    </ArPageHeader>

    <ArTable :columns="columns" :data="logs" :loading="loading" row-key="id">
      <template #cell-action="{ row }">
        <ArTag :type="row.action === 'ban' ? 'error' : 'success'">
          {{ row.action === 'ban' ? '封禁' : '解封' }}
        </ArTag>
      </template>
      <template #cell-ban_type="{ row }">
        <ArTag :type="row.ban_type === 'auto' ? 'warning' : 'info'">
          {{ row.ban_type === 'auto' ? '自动' : '手动' }}
        </ArTag>
      </template>
    </ArTable>

    <ArPagination
      v-if="total > pageSize"
      :page="page"
      :page-size="pageSize"
      :total="total"
      @update:page="
        page = $event
        loadLogs()
      "
    />
  </div>
</template>
