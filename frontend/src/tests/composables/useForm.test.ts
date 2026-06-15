import { describe, it, expect, vi } from 'vitest'
import { useForm } from '@/lib/composables/useForm'

describe('useForm', () => {
  it('初始状态：model 为初始值的拷贝，submitting 为 false，formRef 为 null', () => {
    const initial = { name: 'test', age: 18 }
    const form = useForm(initial)

    expect(form.model.value).toEqual({ name: 'test', age: 18 })
    expect(form.submitting.value).toBe(false)
    expect(form.formRef.value).toBeNull()

    // 修改 model 不应影响原始对象
    form.model.value.name = 'changed'
    expect(initial.name).toBe('test')
  })

  it('reset() 将 model 恢复为初始值', () => {
    const initial = { name: 'test', age: 18 }
    const form = useForm(initial)

    form.model.value.name = 'changed'
    form.model.value.age = 99
    form.reset()

    expect(form.model.value).toEqual({ name: 'test', age: 18 })
  })

  it('submit() 执行过程中 submitting 为 true，结束后为 false', async () => {
    const form = useForm({ value: 1 })
    const handler = vi.fn().mockResolvedValue(undefined)

    const promise = form.submit(handler)
    expect(form.submitting.value).toBe(true)

    await promise
    expect(form.submitting.value).toBe(false)
  })

  it('submit() 将当前 model 传给 handler', async () => {
    const form = useForm({ value: 1 })
    const handler = vi.fn().mockResolvedValue(undefined)

    form.model.value.value = 42
    await form.submit(handler)

    expect(handler).toHaveBeenCalledWith({ value: 42 })
  })

  it('submit() 即使 handler 抛出异常，submitting 也会重置为 false', async () => {
    const form = useForm({ value: 1 })
    const handler = vi.fn().mockRejectedValue(new Error('fail'))

    await expect(form.submit(handler)).rejects.toThrow('fail')
    expect(form.submitting.value).toBe(false)
  })
})
