import { ref } from 'vue'
import type { FormInst } from 'naive-ui'

export const useForm = <T extends Record<string, any>>(initialValue: T) => {
  const formRef = ref<FormInst | null>(null)
  const model = ref<T>({ ...initialValue })
  const submitting = ref(false)

  const reset = () => {
    model.value = { ...initialValue }
  }

  // eslint-disable-next-line no-unused-vars
  type SubmitHandler = (_value: T) => Promise<void>

  const submit = async (handler: SubmitHandler) => {
    submitting.value = true
    try {
      await formRef.value?.validate()
      await handler(model.value)
    } finally {
      submitting.value = false
    }
  }

  return {
    formRef,
    model,
    submitting,
    reset,
    submit
  }
}
