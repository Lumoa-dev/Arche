<script setup lang="ts">
/**
 * PipelineProgress — 流水线进度弹窗
 *
 * GitHub Actions 风格：小圆点 + 任务描述，逐阶段展示。
 * 支持隐藏到后台（静默模式），完成后可通知用户。
 */
import { ref, computed, watch } from 'vue'
import type { PipelineProgress, StageProgress } from '@/lib/pipeline'
import ArButton from '@/components/ui/ArButton.vue'

const props = defineProps<{
  visible: boolean
  progress: PipelineProgress | null
  title?: string
}>()

const emit = defineEmits<{
  close: []
  hide: []
}>()

const minimized = ref(false)

const currentStage = computed(() => {
  if (!props.progress) return null
  const running = props.progress.stages.find((s) => s.status === 'running')
  const done = props.progress.stages.filter((s) => s.status === 'done').length
  const total = props.progress.stages.length
  if (!running && done === total) return null
  return running || null
})

const allDone = computed(() => {
  if (!props.progress) return false
  return props.progress.stages.every((s) => s.status === 'done')
})

const hasError = computed(() => {
  return props.progress?.stages.some((s) => s.status === 'error') || !!props.progress?.error
})

// 自动关闭
watch(allDone, (done) => {
  if (done) {
    setTimeout(() => {
      emit('close')
    }, 1500)
  }
})

function toggleMinimized() {
  minimized.value = !minimized.value
}

function statusIcon(stage: StageProgress): string {
  switch (stage.status) {
    case 'pending':
      return '○'
    case 'running':
      return '●'
    case 'done':
      return '✓'
    case 'error':
      return '✗'
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="pipeline-overlay" @click.self="emit('close')">
        <div class="pipeline-dialog" :class="{ 'pipeline-dialog--minimized': minimized }">
          <!-- 标题栏 -->
          <div class="pipeline-header">
            <span class="pipeline-title">{{ title || '正在处理内容...' }}</span>
            <div class="pipeline-header-actions">
              <ArButton size="xs" type="ghost" icon @click="toggleMinimized">
                <template #icon>
                  <svg
                    v-if="!minimized"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                  <svg
                    v-else
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                  >
                    <polyline points="18 15 12 9 6 15" />
                  </svg>
                </template>
              </ArButton>
              <ArButton size="xs" type="ghost" icon @click="emit('hide')" title="后台运行">
                <template #icon>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                  >
                    <path
                      d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"
                    />
                    <path
                      d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"
                    />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                </template>
              </ArButton>
            </div>
          </div>

          <!-- 缩略模式：仅显示当前阶段 -->
          <div v-if="minimized" class="pipeline-minimized">
            <div v-if="allDone" class="minimized-all-done">✓ 处理完成</div>
            <div v-else-if="hasError" class="minimized-error">✗ 处理失败</div>
            <div v-else class="minimized-running">
              <span class="minimized-spinner" />
              <span>{{ currentStage?.message || '处理中...' }}</span>
            </div>
          </div>

          <!-- 展开模式：完整进度 -->
          <div v-else class="pipeline-stages">
            <div
              v-for="stage in progress?.stages || []"
              :key="stage.stage"
              class="pipeline-stage"
              :class="`pipeline-stage--${stage.status}`"
            >
              <!-- 状态图标 -->
              <div class="stage-icon">
                <span v-if="stage.status === 'running'" class="stage-spinner" />
                <span v-else class="stage-icon-text">{{ statusIcon(stage) }}</span>
              </div>
              <!-- 阶段内容 -->
              <div class="stage-body">
                <div class="stage-label">{{ stage.label }}</div>
                <div v-if="stage.message && stage.status !== 'pending'" class="stage-message">
                  {{ stage.message }}
                </div>
                <!-- 子步骤（预留） -->
                <div v-if="stage.substeps && stage.substeps.length > 0" class="stage-substeps">
                  <div
                    v-for="(sub, si) in stage.substeps"
                    :key="si"
                    class="substep"
                    :class="{ 'substep--done': sub.done }"
                  >
                    <span class="substep-indicator">{{ sub.done ? '✓' : '○' }}</span>
                    {{ sub.label }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部操作 -->
          <div v-if="!minimized" class="pipeline-footer">
            <ArButton v-if="hasError" size="sm" type="ghost" @click="emit('close')">
              关闭
            </ArButton>
            <ArButton v-else-if="allDone" size="sm" type="primary" @click="emit('close')">
              完成
            </ArButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.pipeline-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}

.pipeline-dialog {
  width: 420px;
  max-width: 90vw;
  background: var(--surface-color, #fff);
  border-radius: var(--radius-md, 12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.pipeline-dialog--minimized {
  width: 280px;
}

/* ── 标题栏 ── */

.pipeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, rgba(0, 0, 0, 0.08));
}

.pipeline-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #333);
}

.pipeline-header-actions {
  display: flex;
  gap: 4px;
}

/* ── 缩略模式 ── */

.pipeline-minimized {
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
}

.minimized-running {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary, #666);
}

.minimized-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color, #ddd);
  border-top-color: var(--primary-color, #667eea);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.minimized-all-done {
  color: var(--success-color, #52c41a);
  font-weight: 500;
}

.minimized-error {
  color: var(--error-color, #ff4d4f);
  font-weight: 500;
}

/* ── 阶段列表 ── */

.pipeline-stages {
  padding: 12px 16px;
}

.pipeline-stage {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  min-height: 36px;
  align-items: flex-start;
}

.stage-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.stage-icon-text {
  font-size: 13px;
  line-height: 1;
}

.pipeline-stage--pending .stage-icon-text {
  color: var(--text-quaternary, #bbb);
}

.pipeline-stage--done .stage-icon-text {
  color: var(--success-color, #52c41a);
}

.pipeline-stage--error .stage-icon-text {
  color: var(--error-color, #ff4d4f);
}

.stage-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color, #ddd);
  border-top-color: var(--primary-color, #667eea);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.stage-body {
  flex: 1;
  min-width: 0;
}

.stage-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #333);
  line-height: 1.4;
}

.pipeline-stage--pending .stage-label {
  color: var(--text-tertiary, #999);
}

.pipeline-stage--done .stage-label,
.pipeline-stage--done .stage-message {
  color: var(--text-secondary, #666);
}

.stage-message {
  font-size: 12px;
  color: var(--text-tertiary, #999);
  margin-top: 2px;
}

/* ── 子步骤 ── */

.stage-substeps {
  margin-top: 6px;
  padding-left: 4px;
}

.substep {
  font-size: 12px;
  color: var(--text-tertiary, #999);
  padding: 2px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.substep--done {
  color: var(--text-secondary, #666);
}

.substep-indicator {
  flex-shrink: 0;
  width: 14px;
  text-align: center;
}

/* ── 底部 ── */

.pipeline-footer {
  padding: 10px 16px;
  border-top: 1px solid var(--border-color, rgba(0, 0, 0, 0.08));
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* ── 动画 ── */

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
