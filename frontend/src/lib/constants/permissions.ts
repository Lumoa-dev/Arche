export const API_PERMISSION = {
  AUTH_ME: 'auth:me',
  AUTH_USERS_LIST: 'auth:users:list',
  AUTH_USERS_UPDATE: 'auth:users:update',
  BLOG_POSTS_READ: 'blog:posts:read',
  BLOG_POSTS_WRITE: 'blog:posts:write',
  BLOG_POSTS_MODERATE: 'blog:posts:moderate',
  ASSETS_READ: 'assets:read',
  SYSTEM_READ: 'system:read',
  CONFIG_READ: 'config:read',
  CRAWLER_READ: 'crawler:read'
} as const

export const ROLE_LEVEL = {
  admin: 0,
  user: 1,
  guest: 2
} as const

export const resolveRoleByLevel = (level: number) => {
  if (level <= ROLE_LEVEL.admin) return 'admin'
  if (level <= ROLE_LEVEL.user) return 'user'
  return 'guest'
}
