<script setup lang="ts">
/**
 * ArFormItem — 表单字段包装器
 *
 * 配合 ArForm 使用，自动从表单上下文获取校验状态。
 * 包装 ArInput / ArSelect 等输入组件。
 */
import { inject, ref, onMounted, computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 字段标签 */
    label?: string
    /** 字段名（对应 model 中的 key） */
    prop?: string
    /** 是否必填（仅影响显示，校验由 ArForm rules 控制） */
    required?: boolean
    /** 是否显示校验反馈 */
    showFeedback?: boolean
  }>(),
  {
    label: '',
    prop: '',
    required: false,
    showFeedback: true
  }
)

// 从 ArForm 注入上下文
const form: {
  model: Record<string, unknown>
  errors: Record<string, string[]>
  labelWidth: string
  labelPosition: string
  validateField: (_field: string) => Promise<boolean>
  clearValidate: (_field?: string) => void
} | null = inject('arForm', null)

const fieldErrors = computed(() => {
  if (!form || !props.prop) return []
  return form.errors[props.prop] || []
})

const hasError = computed(() => fieldErrors.value.length > 0)

onMounted(() => {
  if (props.prop && form) {
    // 值变化时清除对应字段的错误
    // watch 会在使用 ArFormItem 的组件中由用户自行决定
  }
})
</script>

<template>
  <div
    class="ar-form-item"
    :class="{
      'ar-form-item--error': hasError,
      'ar-form-item--label-top': form?.labelPosition === 'top'
    }"
  >
    <label
      v-if="label"
      class="ar-form-item__label"
      :class="{ 'ar-form-item__label--required': required }"
    >
      {{ label }}
    </label>
    <div class="ar-form-item__content">
      <slot />
      <transition name="fade-transform">
        <p v-if="showFeedback && hasError" class="ar-form-item__error">
          {{ fieldErrors[0] }}
        </p>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.ar-form-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ar-form-item--label-top {
  flex-direction: column;
}

/* 标签 */
.ar-form-item__label {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-text-primary);
  line-height: 1.4;
  flex-shrink: 0;
}

.ar-form-item__label--required::after {
  content: ' *';
  color: var(--color-danger);
}

/* 内容区（输入控件 + 错误提示） */
.ar-form-item__content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* 错误提示 */
.ar-form-item__error {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-danger);
  line-height: 1.4;
}
</style>
