import type { BlogPost } from '@/components/logic/api/blog'

export interface MockAuthor {
  name: string
  avatar?: string
}

export interface MockExploreItem {
  id: number
  title: string
  author: string
  tags: string[]
  date: string
  likes: number
  favorites: number
  content: string
  excerpt: string
  cover: string
}

export interface MockBlogData {
  posts: BlogPost[]
  exploreItems: MockExploreItem[]
  tags: string[]
  authors: string[]
}

export interface MockAuthData {
  users: Record<
    string,
    {
      id: string
      username: string
      nickname: string
      level: number
      permissions: string[]
    }
  >
}
