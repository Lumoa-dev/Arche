<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NGrid, NGi, NTabPane, NTabs, useMessage } from 'naive-ui'
import { ArButton, ArTable, ArPagination } from '@/components/ui'
import ArCard from '@/components/ui/ArCard.vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import ArHBox from '@/components/ui/ArHBox.vue'
import StatCard from '@/components/widgets/admin/StatCard.vue'
import { getAssetsApi, getAssetStatsApi, type AssetStats } from '@/lib/services/api'
import {
  getOssAdminStatsApi,
  getOssAdminFilesApi,
  getOssAdminTopUsersApi,
  deleteOssAdminFileApi,
  type OSSAdminStats,
  type OSSFile,
  type OSSTopUser
} from '@/lib/services/api'

const message = useMessage()
const activeTab = ref('assets')

// ── 资产管理 ──
const assetStats = ref<AssetStats>({ total: 0, by_type: {} })
const assetPage = ref(1)
const assetPageSize = ref(10)
const assetTotal = ref(0)
const assetList = ref<any[]>([])

const fetchAssetList = async () => {
  try {
    const res = await getAssetsApi(
      { page: assetPage.value, page_size: assetPageSize.value },
      { silent: true, skipAuthLogout: true }
    )
    assetList.value = res.list || []
    assetTotal.value = res.total || 0
  } catch {
    assetList.value = []
    assetTotal.value = 0
  }
}

const onAssetPageChange = (page: number) => {
  assetPage.value = page
  fetchAssetList()
}

const onAssetPageSizeChange = (size: number) => {
  assetPageSize.value = size
  assetPage.value = 1
  fetchAssetList()
}

const assetColumns = [
  { title: '名称', key: 'name', ellipsis: true },
  { title: '类型', key: 'asset_type', width: 120 },
  { title: '创建时间', key: 'created_at', width: 160 }
]

const typeLabelMap: Record<string, string> = {
  blog_post: '博客帖子',
  file: '文件',
  crawl_result: '爬取结果',
  training_job: '训练任务',
  dataset: '数据集',
  artifact: '构建产物',
  config: '配置',
  code_repo: '代码仓库',
  oss_file: 'OSS文件',
  monitor_template: '监控模板',
  training_instance: '训练实例'
}

const assetTypeEntries = ref<{ type: string; count: number; label: string }[]>([])

const fetchAssetData = async () => {
  try {
    const statsRes = await getAssetStatsApi({ silent: true, skipAuthLogout: true })
    assetStats.value = statsRes
    assetTypeEntries.value = Object.entries(statsRes.by_type || {}).map(([type, value]) => ({
      type,
      count: typeof value === 'object' ? value.count : value,
      label: typeLabelMap[type] || type
    }))
  } catch {
    // 静默
  }
}

// ── OSS 存储管理 ──
const ossStats = ref<OSSAdminStats>({ total_files: 0, total_size: 0, total_users: 0 })
const ossTopUsers = ref<OSSTopUser[]>([])
const ossLoading = ref(false)

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

const ossStatCards = [
  { label: '文件总数', value: () => ossStats.value.total_files },
  { label: '总存储', value: () => formatBytes(ossStats.value.total_size) },
  { label: '用户数', value: () => ossStats.value.total_users }
]

const ossFileColumns = [
  { title: '文件名', key: 'path', ellipsis: true },
  { title: 'MIME', key: 'mime_type', width: 120 },
  { title: '大小', key: 'size', width: 100, render: (row: OSSFile) => formatBytes(row.size) },
  { title: '存储', key: 'storage_type', width: 80 },
  {
    title: '私有',
    key: 'is_private',
    width: 60,
    render: (row: OSSFile) => (row.is_private ? '是' : '否')
  },
  { title: '上传时间', key: 'created_at', width: 160 },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (row: OSSFile) =>
      h(
        ArButton,
        { size: 'sm', type: 'danger', onClick: () => handleDeleteOssFile(row) },
        { default: () => '删除' }
      )
  }
]

const ossTopUserColumns = [
  { title: '用户', key: 'username' },
  { title: '文件数', key: 'file_count', width: 100 },
  {
    title: '存储量',
    key: 'total_size',
    width: 120,
    render: (row: OSSTopUser) => formatBytes(row.total_size)
  }
]

// ── OSS 文件分页 ──
const ossFilePage = ref(1)
const ossFilePageSize = ref(10)
const ossFileTotal = ref(0)
const ossFileList = ref<OSSFile[]>([])

const fetchOssFileList = async () => {
  try {
    const res = await getOssAdminFilesApi(
      { page: ossFilePage.value, page_size: ossFilePageSize.value },
      { silent: true, skipAuthLogout: true }
    )
    ossFileList.value = res.files || []
    ossFileTotal.value = res.total || 0
  } catch {
    ossFileList.value = []
    ossFileTotal.value = 0
  }
}

const onOssFilePageChange = (page: number) => {
  ossFilePage.value = page
  fetchOssFileList()
}

const onOssFilePageSizeChange = (size: number) => {
  ossFilePageSize.value = size
  ossFilePage.value = 1
  fetchOssFileList()
}

const handleDeleteOssFile = async (file: OSSFile) => {
  try {
    await deleteOssAdminFileApi(file.id, { silent: true })
    message.success('已删除')
  } catch {
    message.error('删除失败')
  }
}

const fetchOssData = async () => {
  ossLoading.value = true
  try {
    const [statsRes, topRes] = await Promise.all([
      getOssAdminStatsApi({ silent: true, skipAuthLogout: true }),
      getOssAdminTopUsersApi({ silent: true, skipAuthLogout: true })
    ])
    ossStats.value = statsRes
    ossTopUsers.value = topRes || []
  } catch {
    // 静默
  } finally {
    ossLoading.value = false
  }
}

onMounted(() => {
  fetchAssetData()
  fetchAssetList()
  fetchOssData()
  fetchOssFileList()
})
</script>

<template>
  <div>
    <NTabs v-model:value="activeTab" type="line" animated>
      <NTabPane tab="资源列表" name="assets">
        <ArVBox gap="var(--spacing-md)">
          <NGrid :cols="assetTypeEntries.length + 1" :x-gap="12" :y-gap="12">
            <NGi>
              <StatCard label="资产总数" :value="assetStats.total" />
            </NGi>
            <NGi v-for="entry in assetTypeEntries" :key="entry.type">
              <StatCard :label="entry.label" :value="entry.count" />
            </NGi>
          </NGrid>

          <ArCard variant="elevated" style="padding: var(--spacing-md)">
            <ArTable
              :columns="assetColumns"
              :data="assetList"
              :loading="false"
              :row-key="(row: any) => row.id"
              :bordered="false"
            />
            <ArHBox justify="center" style="padding-top: var(--spacing-md)">
              <ArPagination
                :page="assetPage"
                :page-size="assetPageSize"
                :item-count="assetTotal"
                :page-sizes="[10, 20, 50]"
                @update:page="onAssetPageChange"
                @update:page-size="onAssetPageSizeChange"
              />
            </ArHBox>
          </ArCard>
        </ArVBox>
      </NTabPane>

      <NTabPane tab="OSS 存储" name="oss">
        <ArVBox gap="var(--spacing-md)">
          <NGrid :cols="3" :x-gap="12" :y-gap="12">
            <NGi v-for="card in ossStatCards" :key="card.label">
              <StatCard :label="card.label" :value="card.value()" />
            </NGi>
          </NGrid>

          <ArCard variant="elevated" style="padding: var(--spacing-md)">
            <h3
              style="
                margin: 0 0 var(--spacing-sm);
                font-size: 16px;
                font-weight: var(--font-weight-semibold);
                color: var(--text-primary);
              "
            >
              文件列表
            </h3>
            <ArTable
              :columns="ossFileColumns"
              :data="ossFileList"
              :loading="ossLoading"
              :row-key="(row: any) => row.id"
              :bordered="false"
            />
            <ArHBox justify="center" style="padding-top: var(--spacing-md)">
              <ArPagination
                :page="ossFilePage"
                :page-size="ossFilePageSize"
                :item-count="ossFileTotal"
                :page-sizes="[10, 20, 50]"
                @update:page="onOssFilePageChange"
                @update:page-size="onOssFilePageSizeChange"
              />
            </ArHBox>
          </ArCard>

          <ArCard variant="elevated" style="padding: var(--spacing-md)">
            <h3
              style="
                margin: 0 0 var(--spacing-sm);
                font-size: 16px;
                font-weight: var(--font-weight-semibold);
                color: var(--text-primary);
              "
            >
              存储排行 TOP 10
            </h3>
            <ArTable
              :columns="ossTopUserColumns"
              :data="ossTopUsers"
              :row-key="(row: any) => row.user_id"
              :bordered="false"
            />
          </ArCard>
        </ArVBox>
      </NTabPane>
    </NTabs>
  </div>
</template>
