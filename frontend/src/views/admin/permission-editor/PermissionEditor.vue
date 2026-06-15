<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import {
  ArButton,
  ArCard,
  ArSwitch,
  ArTag,
  ArVBox,
  ArHBox,
  ArSpacer,
  ArGrid
} from '@/components/ui'
import { get, put } from '@/lib/services/request'

const message = useMessage()

// ── 状态 ──

interface PageComponent {
  name: string
  visible: boolean
}

interface PageGroup {
  pageName: string
  components: PageComponent[]
}

const levels = ref<number[]>([0])
const selectedLevel = ref<number>(0)
const pageGroups = ref<PageGroup[]>([])
const loading = ref(false)
const saving = ref(false)

// ── 计算属性 ──

const totalPages = computed(() => pageGroups.value.length)
const totalComponents = computed(() =>
  pageGroups.value.reduce((sum, g) => sum + g.components.length, 0)
)
const visibleComponents = computed(() =>
  pageGroups.value.reduce((sum, g) => sum + g.components.filter((c) => c.visible).length, 0)
)

// ── 数据加载 ──

async function loadLevels() {
  try {
    const res = await get<number[]>('/auth/permissions/levels')
    levels.value = res.length > 0 ? res : [0]
    if (!levels.value.includes(selectedLevel.value)) {
      selectedLevel.value = levels.value[0]
    }
  } catch {
    levels.value = [0]
  }
}

async function loadPagePermissions(level: number) {
  loading.value = true
  try {
    const res = await get<Record<string, Record<string, boolean>>>('/auth/permissions/pages', {
      level
    })
    pageGroups.value = Object.entries(res).map(([pageName, components]) => ({
      pageName,
      components: Object.entries(components).map(([name, visible]) => ({
        name,
        visible
      }))
    }))
  } catch {
    message.error('加载权限数据失败')
    pageGroups.value = []
  } finally {
    loading.value = false
  }
}

async function onLevelChange(level: number) {
  selectedLevel.value = level
  await loadPagePermissions(level)
}

// ── 操作 ──

async function toggleComponent(pageName: string, componentName: string, visible: boolean) {
  saving.value = true
  try {
    await put('/auth/permissions/pages', {
      level: selectedLevel.value,
      page_name: pageName,
      component_name: componentName,
      visible
    })
    message.success(`${componentName} ${visible ? '已开启' : '已关闭'}`)
  } catch {
    message.error('更新失败')
  } finally {
    saving.value = false
  }
}

async function togglePage(pageName: string, visible: boolean) {
  saving.value = true
  try {
    await put('/auth/permissions/pages/batch', {
      level: selectedLevel.value,
      page_name: pageName,
      visible
    })
    // 更新本地状态
    const group = pageGroups.value.find((g) => g.pageName === pageName)
    if (group) {
      group.components.forEach((c) => (c.visible = visible))
    }
    message.success(`${pageName} 所有组件已${visible ? '开启' : '关闭'}`)
  } catch {
    message.error('批量更新失败')
  } finally {
    saving.value = false
  }
}

// ── 初始化 ──

onMounted(async () => {
  await loadLevels()
  await loadPagePermissions(selectedLevel.value)
})
</script>

<template>
  <ArVBox gap="lg">
    <ArPageHeader title="页面权限配置" description="按 Level 级别管理页面和组件的可见性" />

    <!-- Level 选择器 -->
    <ArCard>
      <ArHBox gap="md" align="center">
        <span style="font-weight: 600; white-space: nowrap">选择 Level：</span>
        <ArHBox gap="sm" wrap>
          <ArButton
            v-for="level in levels"
            :key="level"
            :type="selectedLevel === level ? 'primary' : 'default'"
            size="sm"
            @click="onLevelChange(level)"
          >
            P{{ level }}
          </ArButton>
        </ArHBox>
        <ArSpacer />
        <span style="color: #888; font-size: 13px">
          {{ totalPages }} 页 / {{ visibleComponents }}/{{ totalComponents }} 组件可见
        </span>
      </ArHBox>
    </ArCard>

    <!-- 权限列表 -->
    <ArVBox v-if="loading" gap="md" style="text-align: center; padding: 48px 0; color: #888">
      加载中...
    </ArVBox>

    <ArVBox v-else gap="md">
      <ArCard v-for="group in pageGroups" :key="group.pageName" :title="group.pageName">
        <template #header-extra>
          <ArHBox gap="sm" align="center">
            <span style="font-size: 13px; color: #888">
              {{ group.components.filter((c) => c.visible).length }}/{{ group.components.length }}
            </span>
            <ArButton size="xs" @click="togglePage(group.pageName, true)">全部开启</ArButton>
            <ArButton size="xs" @click="togglePage(group.pageName, false)">全部关闭</ArButton>
          </ArHBox>
        </template>

        <ArVBox gap="sm">
          <ArHBox
            v-for="comp in group.components"
            :key="comp.name"
            gap="md"
            align="center"
            style="padding: 4px 0"
          >
            <span style="flex: 1; font-size: 14px">{{ comp.name }}</span>
            <ArSwitch
              :model-value="comp.visible"
              :disabled="saving"
              @update:model-value="
                (val: boolean) => toggleComponent(group.pageName, comp.name, val)
              "
            />
          </ArHBox>
        </ArVBox>
      </ArCard>

      <!-- 空状态 -->
      <ArCard
        v-if="pageGroups.length === 0"
        style="text-align: center; padding: 48px 0; color: #888"
      >
        暂无权限配置数据，请先运行迁移或从其他 Level 切换后重试。
      </ArCard>
    </ArVBox>
  </ArVBox>
</template>
