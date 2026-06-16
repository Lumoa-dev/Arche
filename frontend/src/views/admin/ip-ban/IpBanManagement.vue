<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NIcon } from 'naive-ui'
import { ShieldCheckmarkOutline, SearchOutline, AddOutline } from '@vicons/ionicons5'
import ArTable from '@/components/ui/ArTable.vue'
import ArButton from '@/components/ui/ArButton.vue'
import ArInput from '@/components/ui/ArInput.vue'
import ArSelect from '@/components/ui/ArSelect.vue'
import ArPagination from '@/components/ui/ArPagination.vue'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import ArTag from '@/components/ui/ArTag.vue'
import {
  getIpBansApi,
  banIpApi,
  unbanIpApi,
  batchUnbanApi,
  getIpBanStatsApi,
  type IpBanRecord,
  type IpBanStats
} from '@/lib/services/api/ipBan'

const bans = ref<IpBanRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const keyword = ref('')
const banTypeFilter = ref('')
const isActiveFilter = ref('')
const stats = ref<IpBanStats>({
  total_bans: 0,
  active_bans: 0,
  auto_bans: 0,
  manual_bans: 0,
  today_bans: 0
})

const showBanDialog = ref(false)
const banIpInput = ref('')
const banReason = ref('')
const banDuration = ref<number>(-1)
const banSubmitting = ref(false)

const selectedBanIds = ref<number[]>([])

const banTypeFilterOptions = [
  { label: '全部', value: '' },
  { label: '手动', value: 'manual' },
  { label: '自动', value: 'auto' }
]

const isActiveFilterOptions = [
  { label: '全部', value: '' },
  { label: '活跃', value: 'true' },
  { label: '已过期/解封', value: 'false' }
]

const durationOptions = [
  { label: '永久', value: -1 },
  { label: '10 分钟', value: 10 },
  { label: '30 分钟', value: 30 },
  { label: '1 小时', value: 60 },
  { label: '6 小时', value: 360 },
  { label: '24 小时', value: 1440 },
  { label: '7 天', value: 10080 }
]

async function loadBans() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
      silent: true
    }
    if (keyword.value) params.keyword = keyword.value
    if (banTypeFilter.value) params.ban_type = banTypeFilter.value
    if (isActiveFilter.value) params.is_active = isActiveFilter.value
    const result = await getIpBansApi(params as any)
    bans.value = result.list
    total.value = result.total
  } catch {
    // 静默处理
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await getIpBanStatsApi()
  } catch {
    // 静默处理
  }
}

async function handleBan() {
  if (!banIpInput.value.trim()) return
  banSubmitting.value = true
  try {
    await banIpApi({
      ip_or_cidr: banIpInput.value.trim(),
      reason: banReason.value,
      duration_minutes: banDuration.value
    })
    showBanDialog.value = false
    banIpInput.value = ''
    banReason.value = ''
    banDuration.value = -1
    await loadBans()
    await loadStats()
  } catch {
    // 错误由拦截器处理
  } finally {
    banSubmitting.value = false
  }
}

async function handleUnban(banId: number) {
  try {
    await unbanIpApi(banId)
    await loadBans()
    await loadStats()
  } catch {
    // 静默处理
  }
}

async function handleBatchUnban() {
  if (selectedBanIds.value.length === 0) return
  try {
    await batchUnbanApi({ ban_ids: selectedBanIds.value })
    selectedBanIds.value = []
    await loadBans()
    await loadStats()
  } catch {
    // 静默处理
  }
}

function handleSearch() {
  page.value = 1
  loadBans()
}

function refresh() {
  loadBans()
  loadStats()
}

function onPageUpdate(p: number) {
  page.value = p
  loadBans()
}

onMounted(() => {
  loadBans()
  loadStats()
})

const columns = [
  { key: 'ip_or_cidr', title: 'IP/CIDR' },
  { key: 'ban_type', title: '类型' },
  { key: 'reason', title: '原因' },
  { key: 'banned_by', title: '操作人' },
  { key: 'created_at', title: '封禁时间' },
  { key: 'expires_at', title: '过期时间' },
  { key: 'is_active', title: '状态' },
  { key: 'actions', title: '操作' }
]
</script>

<template>
  <div>
    <ArPageHeader title="IP 封禁管理" description="管理被封禁的 IP 和 CIDR 地址段">
      <ArButton type="primary" @click="showBanDialog = true">
        <template #icon>
          <NIcon><AddOutline /></NIcon>
        </template>
        封禁 IP
      </ArButton>
      <ArButton @click="refresh"> 刷新 </ArButton>
    </ArPageHeader>

    <div class="filter-bar">
      <ArInput
        v-model="keyword"
        placeholder="搜索 IP/CIDR..."
        style="width: 240px"
        @keyup.enter="handleSearch"
      />
      <ArSelect
        v-model="banTypeFilter"
        :options="banTypeFilterOptions"
        style="width: 120px"
        @update:value="handleSearch"
      />
      <ArSelect
        v-model="isActiveFilter"
        :options="isActiveFilterOptions"
        style="width: 140px"
        @update:value="handleSearch"
      />
      <ArButton type="primary" @click="handleSearch">
        <template #icon>
          <NIcon><SearchOutline /></NIcon>
        </template>
        搜索
      </ArButton>
      <ArButton v-if="selectedBanIds.length > 0" type="danger" @click="handleBatchUnban">
        <template #icon>
          <NIcon><ShieldCheckmarkOutline /></NIcon>
        </template>
        批量解封 ({{ selectedBanIds.length }})
      </ArButton>
    </div>

    <div class="stats-row">
      <ArTag>总计: {{ stats.total_bans }}</ArTag>
      <ArTag color="red">活跃: {{ stats.active_bans }}</ArTag>
      <ArTag color="yellow">自动: {{ stats.auto_bans }}</ArTag>
      <ArTag color="blue">手动: {{ stats.manual_bans }}</ArTag>
      <ArTag color="green">今日新增: {{ stats.today_bans }}</ArTag>
    </div>

    <ArTable :columns="columns" :data="bans" :loading="loading" row-key="id">
      <template #cell-ban_type="{ row }">
        <ArTag :color="row.ban_type === 'auto' ? 'yellow' : 'blue'">
          {{ row.ban_type === 'auto' ? '自动' : '手动' }}
        </ArTag>
      </template>
      <template #cell-is_active="{ row }">
        <ArTag :color="row.is_active ? 'red' : 'default'">
          {{ row.is_active ? '封禁中' : '已解封' }}
        </ArTag>
      </template>
      <template #cell-actions="{ row }">
        <div style="display: flex; gap: 8px">
          <ArButton v-if="row.is_active" size="sm" type="danger" @click="handleUnban(row.id)">
            解封
          </ArButton>
        </div>
      </template>
    </ArTable>

    <ArPagination
      v-if="total > pageSize"
      :page="page"
      :page-size="pageSize"
      :item-count="total"
      @update:page="onPageUpdate"
    />

    <!-- 封禁对话框 -->
    <div v-if="showBanDialog" class="modal-overlay" @click="showBanDialog = false">
      <div class="modal-content" @click.stop>
        <h3>封禁 IP</h3>
        <div class="form-field">
          <label>IP / CIDR</label>
          <ArInput v-model="banIpInput" placeholder="例如: 192.168.1.1 或 192.168.1.0/24" />
        </div>
        <div class="form-field">
          <label>原因</label>
          <ArInput v-model="banReason" placeholder="封禁原因（可选）" />
        </div>
        <div class="form-field">
          <label>封禁时长</label>
          <ArSelect v-model="banDuration" :options="durationOptions" placeholder="选择封禁时长" />
        </div>
        <div class="modal-actions">
          <ArButton @click="showBanDialog = false">取消</ArButton>
          <ArButton
            type="primary"
            :disabled="!banIpInput.trim() || banSubmitting"
            @click="handleBan"
          >
            确认封禁
          </ArButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stats-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  padding: 24px;
  width: 480px;
  max-width: 90vw;
  box-shadow: var(--shadow-lg);
}

.modal-content h3 {
  margin: 0 0 20px;
  font-size: 18px;
  color: var(--text-primary);
}

.form-field {
  margin-bottom: 16px;
}

.form-field label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
</style>
