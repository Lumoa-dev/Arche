<script setup lang="ts">
/**
 * ArForm — 表单容器
 *
 * 组合 ArInput / ArSelect / ArRadio / ArCheckbox / ArMultiSelect 使用。
 * 通过 ArFormItem 包装字段，自动管理校验和错误状态。
 */
import { ref, reactive, computed, provide } from 'vue'

export interface FormRule {
  required?: boolean
  min?: number
  max?: number
  pattern?: RegExp
  message?: string
  // eslint-disable-next-line no-unused-vars
  validator?: (_value: unknown) => boolean | string | Promise<boolean | string>
}

export interface FormRules {
  [key: string]: FormRule | FormRule[]
}

type FormErrors = Record<string, string[]>

const props = withDefaults(
  defineProps<{
    /** 表单数据对象 */
    model: Record<string, unknown>
    /** 校验规则 */
    rules?: FormRules
    /** 标签宽度 */
    labelWidth?: string
    /** 标签位置 */
    labelPosition?: 'top' | 'left'
  }>(),
  {
    rules: () => ({}),
    labelWidth: '80px',
    labelPosition: 'top'
  }
)

const emit = defineEmits<{
  submit: [model: Record<string, unknown>]
}>()

const errors = reactive<FormErrors>({})
const submitting = ref(false)

/** 获取某个字段的校验规则（统一为数组） */
function getFieldRules(field: string): FormRule[] {
  const rule = props.rules[field]
  if (!rule) return []
  return Array.isArray(rule) ? rule : [rule]
}

/** 校验单个字段 */
async function validateField(field: string): Promise<boolean> {
  const rules = getFieldRules(field)
  if (rules.length === 0) return true

  const value = props.model[field]
  const messages: string[] = []

  for (const rule of rules) {
    if (rule.required) {
      const invalid = value === undefined || value === null || value === ''
      if (invalid) {
        messages.push(rule.message || '此字段必填')
        continue
      }
    }
    if (typeof value === 'string') {
      if (rule.min !== undefined && value.length < rule.min) {
        messages.push(rule.message || `最少 ${rule.min} 个字符`)
      }
      if (rule.max !== undefined && value.length > rule.max) {
        messages.push(rule.message || `最多 ${rule.max} 个字符`)
      }
      if (rule.pattern && !rule.pattern.test(value)) {
        messages.push(rule.message || '格式不正确')
      }
    }
    if (rule.validator) {
      const result = await rule.validator(value)
      if (typeof result === 'string') {
        messages.push(result)
      } else if (!result) {
        messages.push(rule.message || '校验未通过')
      }
    }
  }

  if (messages.length > 0) {
    errors[field] = messages
    return false
  }
  delete errors[field]
  return true
}

/** 校验全部字段 */
async function validate(): Promise<boolean> {
  const fields = Object.keys(props.rules)
  const results = await Promise.all(fields.map((f) => validateField(f)))
  return results.every(Boolean)
}

/** 重置指定字段的错误，不传参则重置全部 */
function clearValidate(field?: string) {
  if (field) {
    delete errors[field]
  } else {
    Object.keys(errors).forEach((k) => delete errors[k])
  }
}

async function handleSubmit() {
  submitting.value = true
  try {
    const valid = await validate()
    if (valid) {
      emit('submit', props.model)
    }
  } finally {
    submitting.value = false
  }
}

// 通过 provide 向 ArFormItem 提供上下文
provide('arForm', {
  model: props.model,
  errors,
  labelWidth: props.labelWidth,
  labelPosition: props.labelPosition,
  validateField,
  clearValidate
})
</script>

<template>
  <form class="ar-form" :class="`ar-form--label-${labelPosition}`" @submit.prevent="handleSubmit">
    <slot />
  </form>
</template>

<style scoped>
.ar-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.ar-form--label-left {
  align-items: flex-start;
}
</style>
