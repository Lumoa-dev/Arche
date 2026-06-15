<template>
  <div class="console-dashboard">
    <ArPageHeader title="控制台" desc="站点运行状态概览" />

    <div class="dashboard-layout">
      <!-- ===== 左栏（主内容，可滚动） ===== -->
      <div class="left-column">
        <!-- 通知/静默区 -->
        <div class="notice-area" @wheel.prevent="onNoticeWheel">
          <!-- 有通知时 -->
          <transition-group
            v-if="displayedNotifications.length > 0"
            name="notice-slide"
            tag="div"
            class="notice-list"
          >
            <div
              v-for="n in displayedNotifications"
              :key="n.id"
              class="notice-card"
              :class="[n.type, { clickable: !!n.route }]"
              @click="n.route && router.push(n.route)"
            >
              <span class="notice-icon">{{ n.icon }}</span>
              <div class="notice-body">
                <span class="notice-title">
                  {{ n.title }}
                  <span v-if="n.count > 1" class="notice-badge">{{ n.count }}</span>
                </span>
                <span class="notice-desc">{{ n.desc }}</span>
              </div>
              <span class="notice-time">{{ n.time }}</span>
              <div class="notice-actions" @click.stop>
                <button class="notice-btn" title="添加到待办" @click="addTodo(n)">📋</button>
                <button class="notice-btn" title="忽略此通知" @click="dismissNotification(n)">
                  ✕
                </button>
              </div>
            </div>
          </transition-group>

          <!-- 无通知时——静默概览区 -->
          <div v-else class="silent-area">
            <div class="silent-item">
              <span class="silent-value">{{ dashboard.online?.online_count ?? '--' }}</span>
              <span class="silent-label">在线用户</span>
            </div>
            <div class="silent-divider" />
            <div class="silent-item">
              <span class="silent-value">{{ dashboard.requests?.current_qps ?? '--' }}</span>
              <span class="silent-label">QPS</span>
            </div>
            <div class="silent-divider" />
            <div class="silent-item">
              <span class="silent-value">{{ formatNumber(dashboard.blog?.total_views ?? 0) }}</span>
              <span class="silent-label">总浏览量</span>
            </div>
            <div class="silent-divider" />
            <div class="silent-item">
              <span class="silent-value">{{ formatNumber(dashboard.blog?.total_posts ?? 0) }}</span>
              <span class="silent-label">帖子总量</span>
            </div>
          </div>
        </div>

        <!-- 曝光率增长趋势（贝塞尔曲线） -->
        <div class="chart-card">
          <div class="chart-header">
            <h2 class="card-title">曝光率增长趋势</h2>
            <div class="chart-tabs">
              <button
                :class="['chart-tab', { active: chartRange === '7d' }]"
                @click="chartRange = '7d'"
              >
                近7天
              </button>
              <button
                :class="['chart-tab', { active: chartRange === '30d' }]"
                @click="chartRange = '30d'"
              >
                近30天
              </button>
            </div>
          </div>
          <div class="chart-body">
            <svg viewBox="0 0 600 240" class="trend-chart">
              <!-- 网格线（5 条，等间距） -->
              <line
                v-for="i in 5"
                :key="'g' + i"
                x1="45"
                :y1="gridY(i)"
                x2="580"
                :y2="gridY(i)"
                stroke="var(--border-color)"
                stroke-width="0.5"
              />
              <!-- Y 轴标签（百分比） -->
              <text
                v-for="(label, i) in yLabels"
                :key="'yl' + i"
                x="40"
                :y="gridY(i) + 4"
                text-anchor="end"
                class="chart-label"
              >
                {{ label }}
              </text>
              <!-- 贝塞尔曲线 -->
              <path
                v-if="bezierPath"
                :d="bezierPath"
                fill="none"
                stroke="var(--primary-color)"
                stroke-width="2.5"
                stroke-linejoin="round"
                stroke-linecap="round"
              />
              <!-- 填充区域 -->
              <path v-if="fillPath" :d="fillPath" fill="url(#gradient)" opacity="0.15" />
              <!-- 渐变定义 -->
              <defs>
                <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="var(--primary-color)" />
                  <stop offset="100%" stop-color="var(--primary-color)" stop-opacity="0" />
                </linearGradient>
              </defs>
              <!-- X 轴标签（仅显示稀疏的标签） -->
              <text
                v-for="(label, i) in chartXLabels"
                :key="'xl' + i"
                :x="chartXPositions[i]"
                y="232"
                text-anchor="middle"
                class="chart-label"
              >
                {{ label }}
              </text>
            </svg>
          </div>
        </div>
      </div>

      <!-- ===== 右栏（固定信息面板） ===== -->
      <div class="right-column">
        <!-- 系统运行状态 -->
        <div class="system-panel">
          <h2 class="card-title">系统运行状态</h2>
          <div class="sys-stats">
            <div class="sys-stat-row">
              <span class="sys-stat-label">运行时间</span>
              <span class="sys-stat-value">{{ formatUptime(dashboard.system?.uptime) }}</span>
            </div>
            <div class="sys-stat-row">
              <span class="sys-stat-label">进程数</span>
              <span class="sys-stat-value">{{ dashboard.system?.process_count ?? '--' }}</span>
            </div>
          </div>
          <div v-for="s in systemBars" :key="s.label" class="sys-bar-row">
            <span class="sys-bar-label">{{ s.label }}</span>
            <div class="sys-bar-track">
              <div class="sys-bar-fill" :style="{ width: s.percent + '%', background: s.color }" />
            </div>
            <span class="sys-bar-pct">{{ s.percent }}%</span>
          </div>
        </div>

        <!-- 吞吐量趋势（QPS） -->
        <div class="qps-panel">
          <div class="qps-header">
            <h2 class="card-title">吞吐量趋势</h2>
            <div class="qps-meta">
              <span class="qps-meta-item"
                >P99 {{ dashboard.requests?.p99_latency_ms ?? '--' }}ms</span
              >
              <span class="qps-meta-item"
                >P50 {{ dashboard.requests?.p50_latency_ms ?? '--' }}ms</span
              >
            </div>
          </div>
          <svg viewBox="0 0 300 120" class="qps-chart">
            <line
              v-for="i in 2"
              :key="'qg' + i"
              x1="35"
              :y1="i * 45"
              x2="285"
              :y2="i * 45"
              stroke="var(--border-color)"
              stroke-width="0.5"
            />
            <rect
              v-for="(pt, i) in qpsBars"
              :key="'qb' + i"
              :x="pt.x"
              :y="pt.y"
              :width="pt.w"
              :height="pt.h"
              fill="var(--primary-color)"
              rx="2"
              opacity="0.7"
            />
            <text x="30" y="14" text-anchor="end" class="chart-label">
              {{ qpsYMax }}
            </text>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import {
  getDashboardApi,
  getNotificationsApi,
  type DashboardData,
  type NotificationItem
} from '@/components/logic/api/system'

const router = useRouter()

// ── Dashboard 数据 ──
const dashboard = ref<DashboardData>({})
const loading = ref(true)

// ── 通知（标准化 API） ──
const notifications = ref<(NotificationItem & { time: string })[]>([])
const dismissedIds = ref<Set<string>>(new Set())

function timeStr() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 已展示的通知（过滤掉被忽略的）
const displayedNotifications = computed(() =>
  notifications.value.filter((n) => !dismissedIds.value.has(n.id))
)

function dismissNotification(n: NotificationItem) {
  dismissedIds.value.add(n.id)
}

function addTodo(n: NotificationItem) {
  const todos = JSON.parse(localStorage.getItem('console_todos') || '[]')
  todos.push({
    id: n.id + '-' + Date.now(),
    title: n.title,
    desc: n.desc,
    route: n.route,
    createdAt: new Date().toISOString()
  })
  localStorage.setItem('console_todos', JSON.stringify(todos))
}

function onNoticeWheel(e: WheelEvent) {
  if (displayedNotifications.value.length > 0 && e.deltaY > 0) {
    const first = displayedNotifications.value[0]
    if (first) dismissNotification(first)
  }
}

// ── 加载数据（5 秒轮询） ──
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchDashboard() {
  try {
    const [dashData, notifData] = await Promise.all([getDashboardApi(), getNotificationsApi()])
    dashboard.value = dashData
    notifications.value = (notifData ?? []).map((n) => ({ ...n, time: timeStr() }))
  } catch {
    // silent failure
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
  pollTimer = setInterval(fetchDashboard, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// ── 工具函数 ──
function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k'
  return String(n)
}

function formatUptime(seconds?: number): string {
  if (!seconds) return '--'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const parts: string[] = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return parts.join(' ')
}

// ── 系统状态条 ──
const systemBars = computed(() => {
  const s = dashboard.value.system
  if (!s) return []
  return [
    { label: 'CPU', percent: Math.round(s.cpu_percent ?? 0), color: '#9a5a2f' },
    { label: '内存', percent: Math.round(s.memory_percent ?? 0), color: '#4f7a57' },
    { label: '磁盘', percent: Math.round(s.disk_percent ?? 0), color: '#1890ff' }
  ]
})

// ── 增长趋势（曝光量曲线，百分比 Y 轴，真实数据） ──
const chartRange = ref<'7d' | '30d'>('7d')

const chartData = computed(() => {
  const trend = chartRange.value === '7d' ? dashboard.value.trend_7d : dashboard.value.trend_30d
  if (!trend || trend.trend.length === 0) return [0] // 无数据时显示平线
  return trend.trend.map((t) => t.views)
})

const chartLabels = computed(() => {
  const trend = chartRange.value === '7d' ? dashboard.value.trend_7d : dashboard.value.trend_30d
  if (!trend || trend.trend.length === 0) return []
  if (chartRange.value === '7d') {
    return trend.trend.map((t) => {
      const d = new Date(t.date)
      const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
      return weekdays[d.getDay()]
    })
  }
  // 30 天只显示 1日, 5日, 10日, 15日, 20日, 25日, 30日
  return trend.trend.map((t, i) => {
    const day = i + 1
    return day % 5 === 1 || day === 1 || day === trend.trend.length ? `${day}日` : ''
  })
})

const padding = { top: 10, bottom: 30, left: 50, right: 10 }
const chartW = 600
const chartH = 240
const chartAreaH = chartH - padding.top - padding.bottom // 200

// Y 轴：0% ~ 100%，5 等分
const yLabels = ['100%', '80%', '60%', '40%', '20%', '0%']

// 将数据值映射到 0~1 的相对值（用于计算百分比 Y 位置）
const normalizedData = computed(() => {
  const max = Math.max(...chartData.value, 1)
  return chartData.value.map((v) => v / max)
})

const gridY = (i: number) => padding.top + (chartAreaH / 5) * i
// i=0 → y=10 (top, 100%), i=5 → y=210 (bottom, 0%)

const chartPoints = computed(() =>
  normalizedData.value.map((ratio, i) => ({
    x:
      padding.left +
      (i / Math.max(normalizedData.value.length - 1, 1)) * (chartW - padding.left - padding.right),
    y: padding.top + chartAreaH * (1 - ratio) // ratio=1 → y=10 (top), ratio=0 → y=210 (bottom)
  }))
)

const chartXPositions = computed(() => chartPoints.value.map((p) => p.x))

const chartXLabels = computed(() => chartLabels.value)

// 贝塞尔平滑曲线路径（点数越多曲度越大，保证"够润"）
function bezierSmooth(points: { x: number; y: number }[]): string {
  if (points.length === 0) return ''
  if (points.length === 1) return `M ${points[0]!.x} ${points[0]!.y}`

  // 根据点数调整张力：点越多 segLen 占比越大，曲线越"润"
  const tension = points.length > 10 ? 2 : 3

  let d = `M ${points[0]!.x} ${points[0]!.y}`
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i]!
    const p1 = points[i + 1]!
    const segLen = (p1.x - p0.x) / tension
    d += ` C ${p0.x + segLen} ${p0.y}, ${p1.x - segLen} ${p1.y}, ${p1.x} ${p1.y}`
  }
  return d
}

const bezierPath = computed(() => bezierSmooth(chartPoints.value))

const fillPath = computed(() => {
  if (!bezierPath.value || chartPoints.value.length === 0) return ''
  const last = chartPoints.value[chartPoints.value.length - 1]
  const first = chartPoints.value[0]
  return `${bezierPath.value} L ${last!.x} ${chartH - padding.bottom} L ${first!.x} ${chartH - padding.bottom} Z`
})

// ── QPS 柱状图 ──
const qpsBars = computed(() => {
  const history = dashboard.value.qps_history ?? []
  if (history.length === 0) return []

  const qpsValues = history.map((h) => h.qps)
  const maxQps = Math.max(...qpsValues, 1)
  const barW = Math.max(4, Math.min(12, 270 / qpsValues.length))
  const gap = 2
  const chartHeight = 90

  return qpsValues.map((qps, i) => {
    const h = (qps / maxQps) * chartHeight
    return {
      x: 35 + i * (barW + gap),
      y: chartHeight - h + 20,
      w: barW,
      h
    }
  })
})

const qpsYMax = computed(() => {
  const values = dashboard.value.qps_history ?? []
  if (values.length === 0) return 0
  return Math.ceil(Math.max(...values.map((h) => h.qps)))
})
</script>

<style scoped>
.console-dashboard {
  max-width: 100%;
}

/* ── 左右分栏 ── */
.dashboard-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 16px;
  align-items: start;
}

.left-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.right-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 0;
}

/* ── 通知/静默区 ── */
.notice-area {
  min-height: 60px;
}

.notice-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notice-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  cursor: default;
  transition: box-shadow 0.15s ease;
}

.notice-card.clickable {
  cursor: pointer;
}

.notice-card.clickable:hover {
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08);
}

.notice-card.warning {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.05);
}

.notice-card.danger {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}

.notice-card.info {
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(59, 130, 246, 0.05);
}

.notice-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.notice-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.notice-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.notice-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: rgba(245, 158, 11, 0.15);
  color: #d97706;
  font-size: 11px;
  font-weight: 700;
}

.notice-desc {
  font-size: 11px;
  color: var(--text-tertiary);
}

.notice-time {
  font-size: 10px;
  color: var(--text-quaternary);
  flex-shrink: 0;
}

.notice-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.notice-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-quaternary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  padding: 0;
}

.notice-btn:hover {
  background: rgba(130, 95, 65, 0.1);
  color: var(--text-secondary);
}

/* 通知进出动画 */
.notice-slide-enter-active,
.notice-slide-leave-active {
  transition: all 0.3s ease;
}

.notice-slide-enter-from {
  opacity: 0;
  transform: translateY(-12px);
}

.notice-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

/* 静默区 */
.silent-area {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 16px 20px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.silent-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.silent-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.silent-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.silent-divider {
  width: 1px;
  height: 36px;
  background: var(--border-color);
}

/* ── 卡片通用 ── */
.chart-card,
.system-panel,
.qps-panel {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

/* ── 图表 ── */
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.chart-tabs {
  display: flex;
  gap: 4px;
}

.chart-tab {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-tertiary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chart-tab.active {
  background: var(--primary-light-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.chart-tab:hover:not(.active) {
  background: var(--surface-strong-color);
}

.chart-body {
  width: 100%;
}

.trend-chart {
  width: 100%;
  height: auto;
  display: block;
}

.chart-label {
  font-size: 10px;
  fill: var(--text-tertiary);
  font-family: inherit;
}

/* ── 系统状态 ── */
.system-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sys-stats {
  display: flex;
  gap: 16px;
}

.sys-stat-row {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.sys-stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.sys-stat-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.sys-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sys-bar-label {
  width: 36px;
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.sys-bar-track {
  flex: 1;
  height: 6px;
  background: var(--bg-color);
  border-radius: 3px;
  overflow: hidden;
}

.sys-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.sys-bar-pct {
  width: 32px;
  font-size: 11px;
  color: var(--text-secondary);
  text-align: right;
  flex-shrink: 0;
}

/* ── QPS ── */
.qps-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.qps-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.qps-meta {
  display: flex;
  gap: 8px;
}

.qps-meta-item {
  font-size: 11px;
  color: var(--text-tertiary);
  padding: 2px 6px;
  background: var(--bg-color);
  border-radius: var(--radius-sm);
}

.qps-chart {
  width: 100%;
  height: auto;
  display: block;
}

/* ── 响应式 ── */
@media (max-width: 900px) {
  .dashboard-layout {
    grid-template-columns: 1fr;
  }

  .right-column {
    position: static;
  }
}
</style>
