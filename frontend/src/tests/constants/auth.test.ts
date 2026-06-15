import { describe, it, expect } from 'vitest'

describe('auth 常量', () => {
  it('AUTH_UNAUTHORIZED_EVENT 值为 auth:unauthorized', async () => {
    const { AUTH_UNAUTHORIZED_EVENT } = await import('@/lib/constants/auth')
    expect(AUTH_UNAUTHORIZED_EVENT).toBe('auth:unauthorized')
  })
})
