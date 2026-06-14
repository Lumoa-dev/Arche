<script setup lang="ts">
import { h, computed, onMounted, ref } from 'vue'
import { useMessage, NModal, NForm, NFormItem, NInput, NSwitch, NPopconfirm } from 'naive-ui'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import { ArButton, ArTable, ArTag } from '@/components/ui'
import type { ArTableColumn } from '@/components/ui/ArTable.vue'
import {
  getConfigListApi,
  getConfigGroupsApi,
  createConfigItemApi,
  updateConfigItemApi,
  deleteConfigItemApi,
  type ConfigItem,
  type ConfigListParams,
  type CreateConfigPayload
} from '@/components/logic/api'

const message = useMessage()

const configs = ref<ConfigItem[]>([])
const groups = ref<string[]>([])
const loading = ref(false)
const selectedGroup = ref<string | null>(null)

interface ConfigForm {
  key: string
  value: string
  group: string
  description: string
  is_sensitive: boolean
}

const emptyForm = (): ConfigForm => ({
  key: '',
  value: '',
  group: 'general',
  description: '',
  is_sensitive: false
})

const showModal = ref(false)
const modalTitle = ref('')
const editingKey = ref<string | null>(null)
const formRef = ref<InstanceType<typeof NForm> | null>(null)
const form = ref<ConfigForm>(emptyForm())
const saving = ref(false)

const groupOptions = computed(() => [
  { label: '全部', value: null },
  ...groups.value.map((g) => ({ label: g, value: g }))
])

const filteredConfigs = computed(() => {
  if (!selectedGroup.value) return configs.value
  return configs.value.filter((c) => c.group === selectedGroup.value)
})

const columns: ArTableColumn[] = [
  { title: '配置键', key: 'key', width: 220, ellipsis: true },
  {
    title: '值',
    key: 'value',
    width: 260,
    ellipsis: true,
    render: (row: ConfigItem) =>
      h(
        'span',
        { class: row.is_sensitive ? 'sensitive-value' : '' },
        row.is_sensitive ? '••••••••' : row.value || '-'
      )
  },
  {
    title: '分组',
    key: 'group',
    width: 100,
    render: (row: ConfigItem) =>
      h(ArTag, { size: 'sm', color: 'default' }, { default: () => row.group || 'general' })
  },
  {
    title: '敏感',
    key: 'is_sensitive',
    width: 70,
    render: (row: ConfigItem) =>
      row.is_sensitive
        ? h(ArTag, { size: 'sm', color: 'red' }, { default: () => '是' })
        : h(ArTag, { size: 'sm', color: 'green' }, { default: () => '否' })
  },
  { title: '描述', key: 'description', width: 200, ellipsis: true },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: (row: ConfigItem) =>
      h('div', { class: 'action-cell' }, [
        h(
          ArButton,
          { size: 'sm', type: 'ghost', onClick: () => openEdit(row) },
          { default: () => '编辑' }
        ),
        h(
          NPopconfirm,
          {
            positiveText: '确认',
            negativeText: '取消',
            onPositiveClick: () => handleDelete(row.key)
          },
          {
            trigger: () =>
              h(
                ArButton,
                { size: 'sm', type: 'ghost', style: { color: 'var(--error-color)' } },
                {
                  default: () => '删除'
                }
              ),
            default: () => `确定删除配置项「${row.key}」？`
          }
        )
      ])
  }
]

async function fetchConfigs() {
  loading.value = true
  try {
    const params: ConfigListParams = {}
    if (selectedGroup.value) {
      params.group = selectedGroup.value
    }
    const res = await getConfigListApi(params, { silent: true })
    configs.value = (res as any)?.data ?? res ?? []
  } catch {
    configs.value = []
  } finally {
    loading.value = false
  }
}

async function fetchGroups() {
  try {
    const res = await getConfigGroupsApi({ silent: true })
    groups.value = (res as any)?.data ?? res ?? []
  } catch {
    groups.value = []
  }
}

function openCreate() {
  editingKey.value = null
  modalTitle.value = '新建配置项'
  form.value = emptyForm()
  showModal.value = true
}

function openEdit(item: ConfigItem) {
  editingKey.value = item.key
  modalTitle.value = '编辑配置项'
  form.value = {
    key: item.key,
    value: item.value,
    group: item.group || 'general',
    description: item.description || '',
    is_sensitive: item.is_sensitive ?? false
  }
  showModal.value = true
}

async function handleSave() {
  if (!form.value.key || !form.value.value) {
    message.warning('请填写配置键和值')
    return
  }
  saving.value = true
  try {
    const payload: CreateConfigPayload = {
      key: form.value.key,
      value: form.value.value,
      group: form.value.group,
      description: form.value.description,
      is_sensitive: form.value.is_sensitive
    }
    if (editingKey.value) {
      await updateConfigItemApi(editingKey.value, form.value.value)
      message.success('更新成功')
    } else {
      await createConfigItemApi(payload)
      message.success('创建成功')
    }
    showModal.value = false
    await fetchConfigs()
    await fetchGroups()
  } catch {
    message.error(editingKey.value ? '更新失败' : '创建失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(key: string) {
  try {
    await deleteConfigItemApi(key)
    message.success(`配置项「${key}」已删除`)
    await fetchConfigs()
    await fetchGroups()
  } catch {
    message.error('删除失败')
  }
}

function handleGroupFilter(group: string | null) {
  selectedGroup.value = group
  fetchConfigs()
}

onMounted(() => {
  fetchGroups()
  fetchConfigs()
})
</script>

<template>
  <div class="config-admin-page">
    <ArPageHeader title="配置管理" desc="管理系统运行时的所有配置项">
      <template #actions>
        <ArButton size="sm" @click="fetchConfigs()">刷新</ArButton>
        <ArButton size="sm" type="primary" @click="openCreate()">+ 新建配置</ArButton>
      </template>
    </ArPageHeader>

    <div class="filter-bar">
      <button
        v-for="opt in groupOptions"
        :key="opt.label ?? '__all'"
        class="filter-btn"
        :class="{ 'filter-btn--active': selectedGroup === opt.value }"
        @click="handleGroupFilter(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>

    <div class="table-section">
      <ArTable :columns="columns" :data="filteredConfigs" :loading="loading" :bordered="false" />
      <div v-if="!loading && filteredConfigs.length === 0" class="empty-hint">暂无配置项</div>
    </div>

    <NModal v-model:show="showModal" :title="modalTitle" preset="card" style="width: 500px">
      <NForm ref="formRef" :model="form" label-placement="top">
        <NFormItem label="配置键" path="key" :rule="[{ required: true, message: '请输入配置键' }]">
          <NInput
            v-model:value="form.key"
            placeholder="如：MY_CONFIG_KEY"
            :disabled="!!editingKey"
          />
        </NFormItem>
        <NFormItem
          label="配置值"
          path="value"
          :rule="[{ required: true, message: '请输入配置值' }]"
        >
          <NInput v-model:value="form.value" placeholder="配置值" />
        </NFormItem>
        <NFormItem label="分组" path="group">
          <NInput v-model:value="form.group" placeholder="general" />
        </NFormItem>
        <NFormItem label="描述" path="description">
          <NInput v-model:value="form.description" placeholder="配置项描述" />
        </NFormItem>
        <NFormItem label="敏感配置" path="is_sensitive">
          <NSwitch v-model:value="form.is_sensitive" />
        </NFormItem>
      </NForm>
      <template #footer>
        <div class="modal-footer">
          <ArButton @click="showModal = false">取消</ArButton>
          <ArButton type="primary" :loading="saving" @click="handleSave">保存</ArButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.config-admin-page {
  max-width: 100%;
}

.filter-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 5px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-color);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.filter-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.filter-btn--active {
  border-color: var(--primary-color);
  background: var(--primary-light-color);
  color: var(--primary-color);
  font-weight: 600;
}

.table-section {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.action-cell {
  display: flex;
  gap: 4px;
  align-items: center;
}

.modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.sensitive-value {
  font-family: var(--font-mono, monospace);
  letter-spacing: 2px;
  color: var(--text-tertiary);
}

.empty-hint {
  text-align: center;
  padding: 40px 0;
  color: var(--text-tertiary);
  font-size: 13px;
}
</style>
