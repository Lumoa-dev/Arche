<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ArTable from '@/components/ui/ArTable.vue'
import ArButton from '@/components/ui/ArButton.vue'
import ArSwitch from '@/components/ui/ArSwitch.vue'
import ArInput from '@/components/ui/ArInput.vue'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import ArTag from '@/components/ui/ArTag.vue'
import { getBanRulesApi, updateBanRuleApi, type AutoBanRule } from '@/lib/services/api/ipBan'

const rules = ref<AutoBanRule[]>([])
const loading = ref(false)
const editingRuleId = ref<string | null>(null)
const editForm = ref<Partial<AutoBanRule>>({})

async function loadRules() {
  loading.value = true
  try {
    const result = await getBanRulesApi()
    if (Array.isArray(result)) {
      rules.value = result
    } else if (result && typeof result === 'object' && 'list' in result) {
      rules.value = (result as any).list
    }
  } catch {
    // 静默处理
  } finally {
    loading.value = false
  }
}

function startEdit(rule: AutoBanRule) {
  editingRuleId.value = rule.id
  editForm.value = {
    enabled: rule.enabled,
    threshold: rule.threshold,
    window_seconds: rule.window_seconds,
    ban_duration_minutes: rule.ban_duration_minutes,
    description: rule.description || undefined,
    name: rule.name
  }
}

function cancelEdit() {
  editingRuleId.value = null
  editForm.value = {}
}

async function saveEdit(ruleId: string) {
  try {
    const payload: Record<string, unknown> = {}
    if (editForm.value.enabled !== undefined) payload.enabled = editForm.value.enabled
    if (editForm.value.threshold !== undefined) payload.threshold = editForm.value.threshold
    if (editForm.value.window_seconds !== undefined)
      payload.window_seconds = editForm.value.window_seconds
    if (editForm.value.ban_duration_minutes !== undefined)
      payload.ban_duration_minutes = editForm.value.ban_duration_minutes
    if (editForm.value.description !== undefined) payload.description = editForm.value.description
    if (editForm.value.name !== undefined) payload.name = editForm.value.name
    await updateBanRuleApi(ruleId, payload as any)
    editingRuleId.value = null
    await loadRules()
  } catch {
    // 错误由拦截器处理
  }
}

function formatWindow(seconds: number): string {
  if (seconds >= 3600) return `${seconds / 3600} 小时`
  if (seconds >= 60) return `${seconds / 60} 分钟`
  return `${seconds} 秒`
}

function formatDuration(minutes: number): string {
  if (minutes === 0) return '仅告警'
  if (minutes >= 1440) return `${minutes / 1440} 天`
  if (minutes >= 60) return `${minutes / 60} 小时`
  return `${minutes} 分钟`
}

onMounted(loadRules)

const columns = [
  { key: 'name', title: '规则名称' },
  { key: 'enabled', title: '启用' },
  { key: 'threshold', title: '阈值' },
  { key: 'window_seconds', title: '统计窗口' },
  { key: 'ban_duration_minutes', title: '封禁时长' },
  { key: 'description', title: '描述' },
  { key: 'actions', title: '操作' }
]
</script>

<template>
  <div>
    <ArPageHeader title="自动封禁规则" description="配置自动封禁规则的触发条件和行为">
      <ArButton @click="loadRules">刷新</ArButton>
    </ArPageHeader>

    <ArTable :columns="columns" :data="rules" :loading="loading" row-key="id">
      <template #cell-enabled="{ row }">
        <template v-if="editingRuleId === row.id">
          <ArSwitch v-model:checked="editForm.enabled" />
        </template>
        <template v-else>
          <ArTag :color="row.enabled ? 'green' : 'default'">
            {{ row.enabled ? '已启用' : '已禁用' }}
          </ArTag>
        </template>
      </template>

      <template #cell-threshold="{ row }">
        <template v-if="editingRuleId === row.id">
          <ArInput v-model="editForm.threshold" type="number" style="width: 80px" />
        </template>
        <template v-else> {{ row.threshold }} 次 </template>
      </template>

      <template #cell-window_seconds="{ row }">
        <template v-if="editingRuleId === row.id">
          <ArInput v-model="editForm.window_seconds" type="number" style="width: 80px" />
        </template>
        <template v-else>
          {{ formatWindow(row.window_seconds) }}
        </template>
      </template>

      <template #cell-ban_duration_minutes="{ row }">
        <template v-if="editingRuleId === row.id">
          <ArInput v-model="editForm.ban_duration_minutes" type="number" style="width: 80px" />
        </template>
        <template v-else>
          {{ formatDuration(row.ban_duration_minutes) }}
        </template>
      </template>

      <template #cell-actions="{ row }">
        <template v-if="editingRuleId === row.id">
          <div style="display: flex; gap: 8px">
            <ArButton size="sm" type="primary" @click="saveEdit(row.id)">保存</ArButton>
            <ArButton size="sm" @click="cancelEdit">取消</ArButton>
          </div>
        </template>
        <template v-else>
          <ArButton size="sm" @click="startEdit(row)">编辑</ArButton>
        </template>
      </template>
    </ArTable>
  </div>
</template>
