<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NTag } from 'naive-ui'
import ArButton from '@/components/ui/ArButton.vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import ArHBox from '@/components/ui/ArHBox.vue'
import ArInput from '@/components/ui/ArInput.vue'
import ArSelect from '@/components/ui/ArSelect.vue'
import ArTable from '@/components/ui/ArTable.vue'
import ArPagination from '@/components/ui/ArPagination.vue'
import ArLineChart from '@/components/ui/ArLineChart.vue'
import ArBarChart from '@/components/ui/ArBarChart.vue'
import {
  queryRequestLogsApi,
  getTopIpsApi,
  getTrendApi,
  getCountersApi,
  listActionsApi,
  type RequestLogItem,
  type IpActionCounterItem,
  type TopIpItem,
  type TrendItem
} from '@/lib/services/api'

const activeTab = ref('logs')

// ── 行为分类选项 ──
const actionOptions = ref<{ label: string; value: string }[]>([])

const loadActions = async () => {
  try {
    const actions = await listActionsApi({ silent: true })
    actionOptions.value = [
      { label: '全部', value: '' },
      ...actions.map((a) => ({ label: a, value: a }))
    ]
  } catch {
    actionOptions.value = [
      { label: '全部', value: '' },
      { label: 'api_call', value: 'api_call' },
      { label: 'page_view', value: 'page_view' },
      { label: 'login_fail', value: 'login_fail' },
      { label: 'other', value: 'other' }
    ]
  }
}

// ── Tab 1: 日志明细 ──
const logFilterIp = ref('')
const logFilterAction = ref('')
const logFilterStart = ref('')
const logFilterEnd = ref('')
const logs = ref<RequestLogItem[]>([])
const logTotal = ref(0)
const logPage = ref(1)
const logLoading = ref(false)

const logColumns = [
  { title: 'IP', key: 'ip', width: 140 },
  { title: '方法', key: 'method', width: 70 },
  { title: '路径', key: 'path', ellipsis: true },
  { title: '状态码', key: 'status_code', width: 80 },
  { title: '耗时(ms)', key: 'duration_ms', width: 90 },
  {
    title: '行为分类',
    key: 'action',
    width: 110,
    render: (row: RequestLogItem) =>
      h(
        NTag,
        { size: 'small', type: row.action === 'login_fail' ? 'error' : 'info' },
        {
          default: () => row.action
        }
      )
  },
  { title: '时间', key: 'created_at', width: 180 }
]

const fetchLogs = async () => {
  logLoading.value = true
  try {
    const res = await queryRequestLogsApi(
      {
        ip: logFilterIp.value || undefined,
        action: logFilterAction.value || undefined,
        start_date: logFilterStart.value || undefined,
        end_date: logFilterEnd.value || undefined,
        page: logPage.value,
        page_size: 20
      },
      { silent: true, skipAuthLogout: true }
    )
    logs.value = res.items || []
    logTotal.value = res.total || 0
  } catch {
    logs.value = []
  } finally {
    logLoading.value = false
  }
}

const onLogSearch = () => {
  logPage.value = 1
  fetchLogs()
}

// ── Tab 2: 聚合计数 ──
const counterFilterIp = ref('')
const counterFilterAction = ref('')
const counterFilterStart = ref('')
const counterFilterEnd = ref('')
const counters = ref<IpActionCounterItem[]>([])
const counterTotal = ref(0)
const counterPage = ref(1)
const counterLoading = ref(false)

const counterColumns = [
  { title: 'IP', key: 'ip', width: 140 },
  {
    title: '行为分类',
    key: 'action',
    width: 110,
    render: (row: IpActionCounterItem) =>
      h(
        NTag,
        { size: 'small', type: row.action === 'login_fail' ? 'error' : 'info' },
        {
          default: () => row.action
        }
      )
  },
  { title: '日期', key: 'action_date', width: 120 },
  { title: '小时', key: 'hour', width: 70 },
  { title: '计数', key: 'count', width: 80 }
]

const fetchCounters = async () => {
  counterLoading.value = true
  try {
    const res = await getCountersApi(
      {
        ip: counterFilterIp.value || undefined,
        action: counterFilterAction.value || undefined,
        start_date: counterFilterStart.value || undefined,
        end_date: counterFilterEnd.value || undefined,
        page: counterPage.value,
        page_size: 20
      },
      { silent: true, skipAuthLogout: true }
    )
    counters.value = res.items || []
    counterTotal.value = res.total || 0
  } catch {
    counters.value = []
  } finally {
    counterLoading.value = false
  }
}

const onCounterSearch = () => {
  counterPage.value = 1
  fetchCounters()
}

// ── Tab 3: TOP IP ──
const topFilterAction = ref('')
const topFilterDays = ref(7)
const topIps = ref<TopIpItem[]>([])
const topLoading = ref(false)

const topColumns = [
  { title: '排名', key: 'rank', width: 60 },
  { title: 'IP', key: 'ip', width: 140 },
  { title: '请求次数', key: 'count', width: 100 }
]

const fetchTopIps = async () => {
  topLoading.value = true
  try {
    const res = await getTopIpsApi(
      {
        action: topFilterAction.value || undefined,
        days: topFilterDays.value,
        limit: 20
      },
      { silent: true, skipAuthLogout: true }
    )
    topIps.value = (res || []).map((item, index) => ({ ...item, rank: index + 1 }))
  } catch {
    topIps.value = []
  } finally {
    topLoading.value = false
  }
}

// ── Tab 4: 趋势 ──
const trendFilterAction = ref('')
const trendFilterDays = ref(7)
const trendData = ref<TrendItem[]>([])
const trendLoading = ref(false)

const fetchTrend = async () => {
  trendLoading.value = true
  try {
    const res = await getTrendApi(
      {
        action: trendFilterAction.value || undefined,
        days: trendFilterDays.value
      },
      { silent: true, skipAuthLogout: true }
    )
    trendData.value = res || []
  } catch {
    trendData.value = []
  } finally {
    trendLoading.value = false
  }
}

// ── Tab 切换时加载数据 ──
const onTabChange = (tab: string) => {
  activeTab.value = tab
  if (tab === 'logs') fetchLogs()
  else if (tab === 'counters') fetchCounters()
  else if (tab === 'topips') fetchTopIps()
  else if (tab === 'trend') fetchTrend()
}

onMounted(() => {
  loadActions()
  fetchLogs()
})
</script>

<template>
  <ArVBox gap="var(--layout-gap)">
    <!-- 导航标签 -->
    <ArCard variant="elevated" style="overflow: hidden">
      <div style="display: flex; gap: 0; border-bottom: 1px solid var(--border-light)">
        <div
          v-for="tab in [
            { key: 'logs', label: '日志明细' },
            { key: 'counters', label: '聚合计数' },
            { key: 'topips', label: 'TOP IP 排行' },
            { key: 'trend', label: '行为趋势' }
          ]"
          :key="tab.key"
          role="button"
          :tabindex="0"
          style="
            padding: 10px 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: var(--font-weight-medium);
            color: var(--text-secondary);
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            user-select: none;
          "
          :style="
            activeTab === tab.key
              ? {
                  color: 'var(--text-primary)',
                  borderBottomColor: 'var(--color-primary)',
                  fontWeight: 'var(--font-weight-semibold)'
                }
              : {}
          "
          @click="onTabChange(tab.key)"
          @keydown.enter="onTabChange(tab.key)"
        >
          {{ tab.label }}
        </div>
      </div>

      <!-- Tab 1: 日志明细 -->
      <div v-if="activeTab === 'logs'" style="padding: 16px">
        <ArVBox gap="var(--spacing-md)">
          <ArHBox gap="var(--spacing-sm)" wrap>
            <ArInput
              v-model="logFilterIp"
              placeholder="按 IP 过滤"
              size="sm"
              style="width: 160px"
              clearable
              @keydown.enter="onLogSearch"
            />
            <ArSelect
              v-model="logFilterAction"
              :options="actionOptions"
              placeholder="行为分类"
              size="sm"
              style="width: 140px"
              clearable
            />
            <ArInput
              v-model="logFilterStart"
              placeholder="开始日期 (YYYY-MM-DD)"
              size="sm"
              style="width: 180px"
              clearable
            />
            <ArInput
              v-model="logFilterEnd"
              placeholder="结束日期 (YYYY-MM-DD)"
              size="sm"
              style="width: 180px"
              clearable
            />
            <ArButton size="sm" @click="onLogSearch">查询</ArButton>
          </ArHBox>
          <ArTable
            :columns="logColumns"
            :data="logs"
            :loading="logLoading"
            size="small"
            striped
            :bordered="false"
            :single-line="true"
          />
          <div style="display: flex; justify-content: flex-end">
            <ArPagination
              :page="logPage"
              :page-size="20"
              :item-count="logTotal"
              @update:page="
                logPage = $event
                fetchLogs()
              "
            />
          </div>
        </ArVBox>
      </div>

      <!-- Tab 2: 聚合计数 -->
      <div v-if="activeTab === 'counters'" style="padding: 16px">
        <ArVBox gap="var(--spacing-md)">
          <ArHBox gap="var(--spacing-sm)" wrap>
            <ArInput
              v-model="counterFilterIp"
              placeholder="按 IP 过滤"
              size="sm"
              style="width: 160px"
              clearable
              @keydown.enter="onCounterSearch"
            />
            <ArSelect
              v-model="counterFilterAction"
              :options="actionOptions"
              placeholder="行为分类"
              size="sm"
              style="width: 140px"
              clearable
            />
            <ArInput
              v-model="counterFilterStart"
              placeholder="开始日期 (YYYY-MM-DD)"
              size="sm"
              style="width: 180px"
              clearable
            />
            <ArInput
              v-model="counterFilterEnd"
              placeholder="结束日期 (YYYY-MM-DD)"
              size="sm"
              style="width: 180px"
              clearable
            />
            <ArButton size="sm" @click="onCounterSearch">查询</ArButton>
          </ArHBox>
          <ArTable
            :columns="counterColumns"
            :data="counters"
            :loading="counterLoading"
            size="small"
            striped
            :bordered="false"
            :single-line="true"
          />
          <div style="display: flex; justify-content: flex-end">
            <ArPagination
              :page="counterPage"
              :page-size="20"
              :item-count="counterTotal"
              @update:page="
                counterPage = $event
                fetchCounters()
              "
            />
          </div>
        </ArVBox>
      </div>

      <!-- Tab 3: TOP IP 排行 -->
      <div v-if="activeTab === 'topips'" style="padding: 16px">
        <ArVBox gap="var(--spacing-md)">
          <ArHBox gap="var(--spacing-sm)" wrap>
            <ArSelect
              v-model="topFilterAction"
              :options="actionOptions"
              placeholder="行为分类"
              size="sm"
              style="width: 140px"
              clearable
            />
            <ArSelect
              v-model="topFilterDays"
              :options="[
                { label: '近 7 天', value: 7 },
                { label: '近 30 天', value: 30 },
                { label: '近 90 天', value: 90 }
              ]"
              placeholder="统计天数"
              size="sm"
              style="width: 120px"
            />
            <ArButton size="sm" @click="fetchTopIps">查询</ArButton>
          </ArHBox>
          <ArHBox gap="var(--spacing-md)">
            <ArCard variant="elevated" style="flex: 1; overflow: hidden">
              <ArBarChart
                :categories="topIps.map((i) => i.ip)"
                :series="[{ name: '请求次数', data: topIps.map((i) => i.count) }]"
                :height="400"
                layout="horizontal"
              />
            </ArCard>
            <ArCard variant="elevated" style="width: 360px; overflow: hidden">
              <ArTable
                :columns="topColumns"
                :data="topIps"
                :loading="topLoading"
                size="small"
                striped
                :bordered="false"
                :single-line="true"
              />
            </ArCard>
          </ArHBox>
        </ArVBox>
      </div>

      <!-- Tab 4: 行为趋势 -->
      <div v-if="activeTab === 'trend'" style="padding: 16px">
        <ArVBox gap="var(--spacing-md)">
          <ArHBox gap="var(--spacing-sm)" wrap>
            <ArSelect
              v-model="trendFilterAction"
              :options="actionOptions"
              placeholder="行为分类"
              size="sm"
              style="width: 140px"
              clearable
            />
            <ArSelect
              v-model="trendFilterDays"
              :options="[
                { label: '近 7 天', value: 7 },
                { label: '近 15 天', value: 15 },
                { label: '近 30 天', value: 30 }
              ]"
              placeholder="统计天数"
              size="sm"
              style="width: 120px"
            />
            <ArButton size="sm" @click="fetchTrend">查询</ArButton>
          </ArHBox>
          <ArCard variant="elevated" style="overflow: hidden">
            <ArLineChart
              :categories="trendData.map((t) => t.date)"
              :series="[{ name: '请求数', data: trendData.map((t) => t.count) }]"
              :height="350"
              show-area
              smooth
              show-mark-line
            />
          </ArCard>
        </ArVBox>
      </div>
    </ArCard>
  </ArVBox>
</template>
