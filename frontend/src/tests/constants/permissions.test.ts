import { describe, it, expect } from 'vitest'

describe('permissions 常量', () => {
  it('API_PERMISSION 包含所有权限键值', async () => {
    const { API_PERMISSION } = await import('@/lib/constants/permissions')
    expect(API_PERMISSION.AUTH_ME).toBe('auth:me')
    expect(API_PERMISSION.AUTH_USERS_LIST).toBe('auth:users:list')
    expect(API_PERMISSION.AUTH_USERS_UPDATE).toBe('auth:users:update')
    expect(API_PERMISSION.BLOG_POSTS_READ).toBe('blog:posts:read')
    expect(API_PERMISSION.BLOG_POSTS_WRITE).toBe('blog:posts:write')
    expect(API_PERMISSION.BLOG_POSTS_MODERATE).toBe('blog:posts:moderate')
    expect(API_PERMISSION.ASSETS_READ).toBe('assets:read')
    expect(API_PERMISSION.SYSTEM_READ).toBe('system:read')
    expect(API_PERMISSION.CONFIG_READ).toBe('config:read')
    expect(API_PERMISSION.CRAWLER_READ).toBe('crawler:read')
  })

  it('ROLE_LEVEL 包含正确等级映射', async () => {
    const { ROLE_LEVEL } = await import('@/lib/constants/permissions')
    expect(ROLE_LEVEL.admin).toBe(0)
    expect(ROLE_LEVEL.user).toBe(1)
    expect(ROLE_LEVEL.guest).toBe(2)
  })

  it('resolveRoleByLevel 根据等级返回正确角色', async () => {
    const { resolveRoleByLevel } = await import('@/lib/constants/permissions')
    expect(resolveRoleByLevel(0)).toBe('admin')
    expect(resolveRoleByLevel(1)).toBe('user')
    expect(resolveRoleByLevel(2)).toBe('guest')
    expect(resolveRoleByLevel(999)).toBe('guest')
  })
})
