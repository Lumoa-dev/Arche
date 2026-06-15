<script setup lang="ts">
import { h, ref } from 'vue'
import { NInput, NPopconfirm, useMessage } from 'naive-ui'
import type { ArTableColumn } from '@/components/ui/ArTable.vue'
import {
  getUsersApi,
  enableUserApi,
  disableUserApi,
  type AdminUser,
  type Paginated
} from '@/components/logic/api'
import { ArButton, ArTag, ArTable, ArPagination } from '@/components/ui'

interface UserRow {
  key: string
  id: string
  username: string
  nickname: string
  email: string
  level: number
  status: string
  createdAt: string
}

const message = useMessage()
const q = ref('')
const users = ref<UserRow[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
let pageSize: number = 10

const columns: ArTableColumn[] = [
  {
    title: '用户名',
    key: 'username',
    ellipsis: true
  },
  {
    title: '昵称',
    key: 'nickname',
    ellipsis: true
  },
  {
    title: '邮箱',
    key: 'email',
    ellipsis: true,
    width: 200
  },
  {
    title: '等级',
    key: 'level',
    width: 100,
    render: (row: UserRow) => {
      const level = row.level ?? 5
      const color = level === 0 ? 'red' : level <= 1 ? 'primary' : 'default'
      const label = level === 0 ? '管理员' : level <= 1 ? '高级用户' : '普通用户'
      return h(ArTag, { color, size: 'sm' }, { default: () => label })
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row: UserRow) => {
      const color = row.status === '活跃' ? 'green' : 'red'
      return h(ArTag, { color, size: 'sm' }, { default: () => row.status })
    }
  },
  {
    title: '创建时间',
    key: 'createdAt',
    width: 120
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: (row: UserRow) => {
      const isActive = row.status === '活跃'
      return h('div', { class: 'action-cell' }, [
        h(
          ArButton,
          {
            type: 'ghost',
            size: 'sm',
            onClick: () => handleEditLevel(row)
          },
          { default: () => '编辑等级' }
        ),
        h(
          NPopconfirm,
          {
            title: '确认操作',
            content: `确定${isActive ? '禁用' : '启用'}用户「${row.username}」吗？`,
            positiveText: '确认',
            negativeText: '取消',
            onPositiveClick: () => handleToggleStatus(row)
          },
          {
            trigger: () =>
              h(
                ArButton,
                { type: isActive ? 'ghost' : 'primary', size: 'sm' },
                { default: () => (isActive ? '禁用' : '启用') }
              )
          }
        )
      ])
    }
  }
]

const toUserRow = (item: AdminUser): UserRow => ({
  key: item.id,
  id: item.id,
  username: item.username,
  nickname: item.nickname || item.username,
  email: item.email || '-',
  level: item.level ?? 5,
  createdAt: item.created_at ? item.created_at.slice(0, 10) : '-',
  status: item.is_active === false ? '禁用' : '活跃'
})

const fetchUsers = async (resetPage = false) => {
  if (resetPage) page.value = 1
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize }
    if (q.value) params.q = q.value
    const res = await getUsersApi(params)
    const paginated = res as unknown as Paginated<AdminUser>
    users.value = (paginated.list || []).map(toUserRow)
    total.value = paginated.total || 0
  } catch {
    message.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleEditLevel = (row: UserRow) => {
  message.info(`编辑用户等级：${row.username}（当前等级 ${row.level}）`)
}

const handleToggleStatus = async (row: UserRow) => {
  try {
    if (row.status === '活跃') {
      await disableUserApi(row.id)
      row.status = '禁用'
      message.success('用户已禁用')
    } else {
      await enableUserApi(row.id)
      row.status = '活跃'
      message.success('用户已启用')
    }
  } catch {
    message.error('更新用户状态失败')
  }
}

const handlePageChange = (p: number) => {
  page.value = p
  fetchUsers()
}
</script>

<template>
  <div class="user-table">
    <div class="toolbar">
      <div class="toolbar-left">
        <NInput
          v-model:value="q"
          placeholder="搜索用户名..."
          clearable
          size="small"
          style="width: 240px"
          @keyup.enter="fetchUsers(true)"
        />
      </div>
      <div class="toolbar-right">
        <ArButton size="sm" @click="fetchUsers()">刷新</ArButton>
      </div>
    </div>

    <div class="table-wrapper">
      <ArTable
        :columns="columns"
        :data="users"
        :loading="loading"
        :bordered="false"
        :single-line="true"
        size="small"
        striped
      />
    </div>

    <div class="pager">
      <ArPagination
        :page="page"
        :page-size="pageSize"
        :item-count="total"
        :page-sizes="[10, 20, 50]"
        @update:page="handlePageChange"
        @update:page-size="
          (v: number) => {
            pageSize = v
            fetchUsers(true)
          }
        "
      />
    </div>
  </div>
</template>

<style scoped>
.user-table {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left {
  display: flex;
  gap: 8px;
  align-items: center;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.table-wrapper {
  background: var(--surface-color);
  border: var(--glass-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.pager {
  display: flex;
  justify-content: center;
  padding-top: 4px;
}

.action-cell {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
