import type { MockAuthData } from './types'

export const authMockData: MockAuthData = {
  users: {
    user: {
      id: '1',
      username: 'user',
      nickname: '普通用户',
      level: 5,
      permissions: ['auth:me', 'blog:posts:read', 'blog:posts:write']
    },
    admin: {
      id: '2',
      username: 'admin',
      nickname: '管理员',
      level: 0,
      permissions: ['*']
    },
    guest: {
      id: '3',
      username: 'guest',
      nickname: '访客',
      level: 5,
      permissions: []
    }
  }
}
