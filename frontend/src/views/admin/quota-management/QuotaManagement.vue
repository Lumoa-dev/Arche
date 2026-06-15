<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NInput, NProgress, useMessage } from 'naive-ui'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import { ArButton, ArTable } from '@/components/ui'
import type { ArTableColumn } from '@/components/ui/ArTable.vue'
import { getOssAdminQuotasApi, updateOssUserQuotaApi, type OSSQuota } from '@/components/logic/api'

const message = useMessage()
const quotas = ref<OSSQuota[]>([])
const loading = ref(false)
const editingUserId = ref<string | null>(null)
const editValue = ref('')

/**
 * 字节数自动转换为可读单位。
 */
function formatBytes(bytes: number): string {
  if (bytes < 0) return '不限'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

/**
 * 将可读字符串解析回字节数。
 * 支持后缀: B, KB, MB, GB（不区分大小写）。
 */
function parseBytes(str: string): number | null {
  const trimmed = str.trim().toUpperCase()
  const match = trimmed.match(/^(\d+(?:\.\d+)?)\s*(B|KB|MB|GB)?$/)
  if (!match) return null
  const value = parseFloat(match[1]!)
  const unit = match[2] || 'B'
  switch (unit) {
    case 'B':
      return value
    case 'KB':
      return value * 1024
    case 'MB':
      return value * 1024 * 1024
    case 'GB':
      return value * 1024 * 1024 * 1024
    default:
      return null
  }
}

const fetchQuotas = async () => {
  loading.value = true
  try {
    const res = await getOssAdminQuotasApi({ silent: true, skipAuthLogout: true })
    quotas.value = res.list || []
  } catch {
    quotas.value = []
  } finally {
    loading.value = false
  }
}

const startEdit = (row: OSSQuota) => {
  editingUserId.value = row.user_id
  editValue.value = formatBytes(row.quota_bytes)
}

const cancelEdit = () => {
  editingUserId.value = null
  editValue.value = ''
}

const saveEdit = async (userId: string) => {
  const bytes = parseBytes(editValue.value)
  if (bytes === null) {
    message.warning('请输入有效的配额值，例如 "500MB"、"2GB"')
    return
  }
  if (bytes < 0) {
    message.warning('配额不能为负数')
    return
  }
  try {
    await updateOssUserQuotaApi(userId, { quota_bytes: bytes }, { silent: true })
    message.success('配额更新成功')
    editingUserId.value = null
    await fetchQuotas()
  } catch {
    message.error('配额更新失败')
  }
}

const handleKeydown = (e: KeyboardEvent, userId: string) => {
  if (e.key === 'Enter') {
    saveEdit(userId)
  }
  if (e.key === 'Escape') {
    cancelEdit()
  }
}

const getUsagePercent = (row: OSSQuota): number => {
  if (row.quota_bytes <= 0) return 0
  return Math.min(row.usage_percent, 100)
}

const columns: ArTableColumn[] = [
  {
    title: '用户 ID',
    key: 'user_id',
    width: 160,
    ellipsis: true,
    render: (row: OSSQuota) => row.username || row.user_id.slice(0, 8)
  },
  {
    title: '用户等级',
    key: 'level',
    width: 100,
    render: () => '-'
  },
  {
    title: '已用空间',
    key: 'used_bytes',
    width: 120,
    render: (row: OSSQuota) => formatBytes(row.used_bytes)
  },
  {
    title: '配额上限',
    key: 'quota_bytes',
    width: 180,
    render: (row: OSSQuota) => {
      if (editingUserId.value === row.user_id) {
        return h(NInput, {
          value: editValue.value,
          size: 'small',
          placeholder: '如 500MB、2GB',
          onUpdateValue: (v: string) => {
            editValue.value = v
          },
          onKeydown: (e: KeyboardEvent) => handleKeydown(e, row.user_id),
          onBlur: () => saveEdit(row.user_id),
          autofocus: true
        })
      }
      return h(
        'span',
        {
          class: 'quota-value',
          style: { cursor: 'pointer', color: 'var(--primary-color)' },
          onClick: () => startEdit(row)
        },
        { default: () => formatBytes(row.quota_bytes) }
      )
    }
  },
  {
    title: '使用率',
    key: 'usage_percent',
    width: 200,
    render: (row: OSSQuota) =>
      h(NProgress, {
        type: 'line',
        percentage: getUsagePercent(row),
        indicatorPlacement: 'inside',
        height: 18,
        processing: false
      })
  }
]

onMounted(() => {
  fetchQuotas()
})
</script>

<template>
  <div class="quota-management-page">
    <ArPageHeader title="配额管理" desc="管理 OSS 用户存储配额">
      <template #actions>
        <ArButton size="sm" type="secondary" @click="fetchQuotas" :loading="loading">
          刷新
        </ArButton>
      </template>
    </ArPageHeader>

    <div class="table-wrapper">
      <ArTable
        :columns="columns"
        :data="quotas"
        :loading="loading"
        :row-key="(row: OSSQuota) => row.user_id"
        :bordered="false"
        :single-line="true"
        striped
      />
    </div>

    <div v-if="quotas.length === 0 && !loading" class="empty-state">
      <p>暂无配额数据</p>
    </div>
  </div>
</template>

<style scoped>
.quota-management-page {
  max-width: 100%;
}

.table-wrapper {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.quota-value {
  text-decoration: underline;
  text-decoration-style: dotted;
  text-underline-offset: 2px;
  transition: opacity var(--transition-fast);
}

.quota-value:hover {
  opacity: 0.75;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
  color: var(--text-tertiary);
}
</style>
