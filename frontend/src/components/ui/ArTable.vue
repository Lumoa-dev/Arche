<script setup lang="ts">
import { computed, ref, watch, nextTick, onMounted } from 'vue'
import ArPagination from './ArPagination.vue'

/* ════════════════════════════════════════
   类型定义
   ════════════════════════════════════════ */

export interface ArTableColumn {
  title: string
  key: string
  width?: number | string
  minWidth?: number | string
  align?: 'left' | 'center' | 'right'
  ellipsis?: boolean
  fixed?: 'left' | 'right'
  sortable?: boolean
  sorter?: (a: any, b: any) => number
  render?: (row: any) => any
  summary?: (rows: any[]) => string | number
}

export type SortOrder = 'asc' | 'desc' | null

export interface PaginationProps {
  page: number
  pageSize: number
  itemCount: number
  pageSizes?: number[]
}

/* ════════════════════════════════════════
   Props & Emits
   ════════════════════════════════════════ */

const props = withDefaults(
  defineProps<{
    columns: ArTableColumn[]
    data: Record<string, any>[]
    loading?: boolean
    rowKey?: string | ((row: any) => string | number)
    bordered?: boolean
    singleLine?: boolean
    striped?: boolean
    size?: 'small' | 'medium' | 'large'
    pagination?: PaginationProps | false
    sortable?: boolean
    selectable?: boolean
    selectedRowKeys?: (string | number)[]
    summary?: boolean
    emptyText?: string
    maxHeight?: string | number
    /** 基于内容自动计算列宽 */
    fitContent?: boolean
  }>(),
  {
    loading: false,
    bordered: false,
    singleLine: true,
    striped: true,
    size: 'small',
    selectable: false,
    summary: false,
    emptyText: '暂无数据',
    fitContent: false
  }
)

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
  'update:selectedRowKeys': [keys: (string | number)[]]
  'update:sorter': [payload: { key: string; order: SortOrder }]
}>()

/* ════════════════════════════════════════
   排序
   ════════════════════════════════════════ */

const sortKey = ref<string | null>(null)
const sortOrder = ref<SortOrder>(null)

function toggleSort(col: ArTableColumn) {
  if (!col.sortable && !props.sortable) return
  if (sortKey.value === col.key) {
    // asc → desc → null
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : sortOrder.value === 'desc' ? null : 'asc'
    if (!sortOrder.value) sortKey.value = null
  } else {
    sortKey.value = col.key
    sortOrder.value = 'asc'
  }
  emit('update:sorter', { key: sortKey.value ?? '', order: sortOrder.value })
}

function getSortIcon(col: ArTableColumn): string {
  if (sortKey.value !== col.key) return 'none'
  return sortOrder.value ?? 'none'
}

/** 客户端排序后的数据 */
const sortedData = computed(() => {
  if (!sortKey.value || !sortOrder.value) return props.data
  const col = props.columns.find((c) => c.key === sortKey.value)
  if (!col) return props.data

  const sorted = [...props.data]
  sorted.sort((a, b) => {
    if (col.sorter) return col.sorter(a, b) * (sortOrder.value === 'asc' ? 1 : -1)
    const va = a[col.key]
    const vb = b[col.key]
    if (va == null) return 1
    if (vb == null) return -1
    if (typeof va === 'number' && typeof vb === 'number')
      return (va - vb) * (sortOrder.value === 'asc' ? 1 : -1)
    return String(va).localeCompare(String(vb)) * (sortOrder.value === 'asc' ? 1 : -1)
  })
  return sorted
})

/* ════════════════════════════════════════
   选择
   ════════════════════════════════════════ */

const internalSelectedKeys = ref<(string | number)[]>([])

const selectedKeys = computed({
  get: () => props.selectedRowKeys ?? internalSelectedKeys.value,
  set: (v) => {
    internalSelectedKeys.value = v
    emit('update:selectedRowKeys', v)
  }
})

function getRowKey(row: any): string | number {
  if (typeof props.rowKey === 'function') return props.rowKey(row)
  if (typeof props.rowKey === 'string') return row[props.rowKey]
  return row.key ?? row.id ?? JSON.stringify(row)
}

function isSelected(row: any): boolean {
  return selectedKeys.value.includes(getRowKey(row))
}

function toggleRow(row: any) {
  const key = getRowKey(row)
  const idx = selectedKeys.value.indexOf(key)
  if (idx >= 0) {
    const next = [...selectedKeys.value]
    next.splice(idx, 1)
    selectedKeys.value = next
  } else {
    selectedKeys.value = [...selectedKeys.value, key]
  }
}

function toggleAll() {
  if (allSelected.value) {
    selectedKeys.value = []
  } else {
    selectedKeys.value = sortedData.value.map((r) => getRowKey(r))
  }
}

const allSelected = computed(() => {
  if (!sortedData.value.length) return false
  return sortedData.value.every((r) => selectedKeys.value.includes(getRowKey(r)))
})

/* ════════════════════════════════════════
   合计行
   ════════════════════════════════════════ */

const summaryData = computed(() => {
  if (!props.summary) return null
  return props.columns.map((col) => {
    if (col.summary) return col.summary(props.data)
    return ''
  })
})

/* ════════════════════════════════════════
   动态列宽（fitContent）
   ════════════════════════════════════════ */

const tableRef = ref<HTMLTableElement | null>(null)
const colWidths = ref<number[]>([])

async function measureColumns() {
  if (!props.fitContent) {
    colWidths.value = []
    return
  }
  await nextTick()
  const el = tableRef.value
  if (!el) return

  const headerCells = el.querySelectorAll<HTMLElement>('thead th')
  const bodyRows = el.querySelectorAll<HTMLElement>('tbody tr')
  const widths: number[] = []

  headerCells.forEach((th, idx) => {
    // 如果是选择列（额外插入的 th），跳过
    let maxW = th.scrollWidth
    bodyRows.forEach((row) => {
      const cell = row.children[idx] as HTMLElement
      if (cell) {
        maxW = Math.max(maxW, cell.scrollWidth)
      }
    })
    widths.push(maxW)
  })

  colWidths.value = widths
}

watch(
  () => [props.data, props.columns, props.fitContent],
  () => {
    if (props.fitContent) measureColumns()
  },
  { deep: true }
)

onMounted(() => {
  if (props.fitContent) measureColumns()
})

/* ════════════════════════════════════════
   列样式辅助
   ════════════════════════════════════════ */

function getColAttrs(col: ArTableColumn) {
  const style: Record<string, string> = {}
  if (col.width != null) style.width = typeof col.width === 'number' ? col.width + 'px' : col.width
  if (col.minWidth != null)
    style.minWidth = typeof col.minWidth === 'number' ? col.minWidth + 'px' : col.minWidth
  return { style }
}

function isSortable(col: ArTableColumn): boolean {
  return col.sortable ?? props.sortable ?? false
}
</script>

<template>
  <div
    class="ar-table"
    :class="[
      `ar-table--${size}`,
      {
        'ar-table--bordered': bordered,
        'ar-table--loading': loading,
        'ar-table--selectable': selectable,
        'ar-table--single-line': singleLine
      }
    ]"
  >
    <div
      class="ar-table__wrapper"
      :style="
        maxHeight
          ? {
              maxHeight: typeof maxHeight === 'number' ? maxHeight + 'px' : maxHeight,
              overflowY: 'auto'
            }
          : {}
      "
    >
      <table ref="tableRef" class="ar-table__table">
        <colgroup v-if="colWidths.length">
          <col v-for="(w, i) in colWidths" :key="i" :style="{ width: w + 'px' }" />
        </colgroup>
        <thead>
          <tr class="ar-table__header-row">
            <!-- 选择列 -->
            <th
              v-if="selectable"
              class="ar-table__header-cell ar-table__cell--check"
              style="width: 40px; min-width: 40px"
            >
              <label class="ar-table__check-wrap">
                <input
                  type="checkbox"
                  class="ar-table__check"
                  :checked="allSelected"
                  :indeterminate="!allSelected && selectedKeys.length > 0"
                  @change="toggleAll"
                />
                <span class="ar-table__check-fake" />
              </label>
            </th>
            <th
              v-for="col in columns"
              :key="col.key"
              class="ar-table__header-cell"
              :class="{
                'ar-table__header-cell--sortable': isSortable(col),
                'ar-table__header-cell--fixed-left': col.fixed === 'left',
                'ar-table__header-cell--fixed-right': col.fixed === 'right'
              }"
              :style="[
                col.fixed === 'left' ? { position: 'sticky', left: 0, zIndex: 3 } : {},
                col.fixed === 'right' ? { position: 'sticky', right: 0, zIndex: 3 } : {},
                getColAttrs(col).style
              ]"
              @click="toggleSort(col)"
            >
              <span class="ar-table__header-title">
                {{ col.title }}
                <span
                  v-if="isSortable(col)"
                  class="ar-table__sort-icon"
                  :class="`ar-table__sort-icon--${getSortIcon(col)}`"
                >
                  <svg width="10" height="14" viewBox="0 0 10 14" fill="none">
                    <path
                      d="M3 10l2 3 2-3"
                      stroke="currentColor"
                      stroke-width="1.5"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      d="M3 4l2-3 2 3"
                      stroke="currentColor"
                      stroke-width="1.5"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </span>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, rowIdx) in sortedData"
            :key="getRowKey(row)"
            class="ar-table__row"
            :class="{
              'ar-table__row--striped': striped && rowIdx % 2 === 1,
              'ar-table__row--selected': isSelected(row)
            }"
          >
            <!-- 选择列 -->
            <td
              v-if="selectable"
              class="ar-table__cell ar-table__cell--check"
              @click.stop="toggleRow(row)"
            >
              <label class="ar-table__check-wrap">
                <input
                  type="checkbox"
                  class="ar-table__check"
                  :checked="isSelected(row)"
                  @change="toggleRow(row)"
                />
                <span class="ar-table__check-fake" />
              </label>
            </td>
            <td
              v-for="col in columns"
              :key="col.key"
              class="ar-table__cell"
              :class="{
                'ar-table__cell--ellipsis': col.ellipsis,
                'ar-table__cell--fixed-left': col.fixed === 'left',
                'ar-table__cell--fixed-right': col.fixed === 'right'
              }"
              :style="[
                { textAlign: col.align || 'left' },
                col.fixed === 'left'
                  ? { position: 'sticky', left: selectable ? 40 : 0, zIndex: 1 }
                  : {},
                col.fixed === 'right' ? { position: 'sticky', right: 0, zIndex: 1 } : {},
                getColAttrs(col).style
              ]"
            >
              <template v-if="col.render">
                <component :is="() => col.render!(row)" />
              </template>
              <span v-else class="ar-table__cell-text">{{ row[col.key] }}</span>
            </td>
          </tr>

          <!-- 合计行 -->
          <tr v-if="summary && summaryData" class="ar-table__row ar-table__row--summary">
            <td v-if="selectable" class="ar-table__cell ar-table__cell--summary" />
            <td
              v-for="(val, idx) in summaryData"
              :key="`summary-${idx}`"
              class="ar-table__cell ar-table__cell--summary"
              :class="columns[idx]?.ellipsis ? 'ar-table__cell--ellipsis' : ''"
              :style="{ textAlign: columns[idx]?.align || 'left' }"
            >
              <span class="ar-table__cell-text">{{ val }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 空态 -->
      <div v-if="!data.length && !loading" class="ar-table__empty">
        <span class="ar-table__empty-text">{{ emptyText }}</span>
      </div>

      <!-- 加载遮罩 -->
      <div v-if="loading" class="ar-table__loading-mask">
        <div class="ar-table__loading-spinner" />
      </div>
    </div>

    <!-- 分页器 -->
    <div v-if="pagination" class="ar-table__pagination">
      <ArPagination
        :page="pagination.page"
        :page-size="pagination.pageSize"
        :item-count="pagination.itemCount"
        :page-sizes="pagination.pageSizes ?? [10, 20, 50]"
        @update:page="(p: number) => emit('update:page', p)"
        @update:page-size="(s: number) => emit('update:pageSize', s)"
      />
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════ 基础 ═══════════════ */
.ar-table {
  font-family: var(--font-sans);
  width: 100%;
}

.ar-table__wrapper {
  overflow-x: auto;
  position: relative;
  min-height: 60px;
}

.ar-table__table {
  width: 100%;
  table-layout: auto;
  border-collapse: collapse;
}

/* ═══════════════ 列宽指示 ═══════════════ */
.ar-table--single-line .ar-table__cell {
  white-space: nowrap;
}

/* ═══════════════ 表头 ═══════════════ */
.ar-table__header-row {
  background: var(--surface-strong-color);
}

.ar-table__header-cell {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  user-select: none;
  background: var(--surface-strong-color);
}

.ar-table__header-cell--sortable {
  cursor: pointer;
  transition: background 0.15s ease;
}

.ar-table__header-cell--sortable:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
}

.ar-table__header-title {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* ── 排序图标 ── */
.ar-table__sort-icon {
  display: inline-flex;
  align-items: center;
  opacity: 0.3;
  transition: opacity 0.15s ease;
}

.ar-table__header-cell--sortable:hover .ar-table__sort-icon {
  opacity: 0.6;
}

.ar-table__sort-icon--asc path:first-child,
.ar-table__sort-icon--desc path:last-child {
  opacity: 0.3;
}

.ar-table__sort-icon--asc path:last-child,
.ar-table__sort-icon--desc path:first-child {
  opacity: 1;
  color: var(--primary-color);
}

/* ═══════════════ 行 ═══════════════ */
.ar-table__row {
  background: var(--surface-color);
  transition: background 0.15s ease;
}

.ar-table__row--striped {
  background: var(--surface-inset-color);
}

.ar-table__row--selected {
  background: var(--primary-light-color);
}

/* ═══════════════ 单元格 ═══════════════ */
.ar-table__cell {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: 13px;
  background: inherit;
}

.ar-table__cell--ellipsis {
  max-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ar-table__cell-text {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 固定列：背景兜底 */
.ar-table__cell--fixed-left,
.ar-table__cell--fixed-right {
  background: inherit;
}

/* ═══════════════ 选择列 ═══════════════ */
.ar-table__cell--check {
  width: 40px;
  min-width: 40px;
  padding: 8px 6px;
  text-align: center;
  vertical-align: middle;
}

.ar-table__check-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  width: 16px;
  height: 16px;
}

.ar-table__check {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
  z-index: 1;
}

.ar-table__check-fake {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-radius: 3px;
  background: var(--surface-color);
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.ar-table__check:checked + .ar-table__check-fake {
  background: var(--primary-color);
  border-color: var(--primary-color);
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 16 16' fill='white' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M6.173 11.54L3.22 8.587l-.827.827 3.78 3.78 7.5-7.5-.827-.827-6.673 6.673z'/%3E%3C/svg%3E");
}

.ar-table__check:indeterminate + .ar-table__check-fake {
  background: var(--primary-color);
  border-color: var(--primary-color);
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 16 16' fill='white' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='3' y='7' width='10' height='2'/%3E%3C/svg%3E");
}

/* ═══════════════ 合计行 ═══════════════ */
.ar-table__row--summary {
  background: var(--surface-inset-color);
  font-weight: 600;
  border-top: 2px solid var(--border-color);
}

.ar-table__row--summary .ar-table__cell {
  font-size: 12px;
  color: var(--text-primary);
}

/* ═══════════════ 尺寸 ═══════════════ */
.ar-table--small .ar-table__header-cell {
  padding: 6px 10px;
}

.ar-table--small .ar-table__cell {
  padding: 6px 10px;
  font-size: 12px;
}

.ar-table--medium .ar-table__header-cell {
  padding: 10px 14px;
}

.ar-table--medium .ar-table__cell {
  padding: 10px 14px;
  font-size: 14px;
}

.ar-table--large .ar-table__header-cell {
  padding: 12px 16px;
}

.ar-table--large .ar-table__cell {
  padding: 12px 16px;
  font-size: 15px;
}

/* ═══════════════ 边框 ═══════════════ */
.ar-table--bordered .ar-table__table {
  border: 1px solid var(--border-color);
}

/* ═══════════════ 空态 ═══════════════ */
.ar-table__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
}

.ar-table__empty-text {
  color: var(--text-tertiary);
  font-size: 13px;
}

/* ═══════════════ 加载态 ═══════════════ */
.ar-table__loading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.5);
}

.ar-table__loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: ar-table-spin 0.6s linear infinite;
}

@keyframes ar-table-spin {
  to {
    transform: rotate(360deg);
  }
}

/* ═══════════════ 分页 ═══════════════ */
.ar-table__pagination {
  display: flex;
  justify-content: center;
}

/* ═══════════════ 固定列 sticky 支持 ═══════════════ */
.ar-table__header-cell--fixed-left,
.ar-table__header-cell--fixed-right {
  position: sticky;
}

.ar-table__cell--fixed-left,
.ar-table__cell--fixed-right {
  position: sticky;
}
</style>
