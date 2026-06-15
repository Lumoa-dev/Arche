<template>
  <div class="assets-page">
    <ArPageHeader title="资源管理" desc="管理用户产生的帖子、评论和静态文件" />

    <!-- Tab 切换 -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        <NIcon size="16"><component :is="tab.icon" /></NIcon>
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <!-- 帖子资产 -->
    <div v-if="activeTab === 'posts'" class="tab-content">
      <div class="stat-row">
        <div class="stat-card">
          <span class="stat-big">456</span><span class="stat-desc">总帖子</span>
        </div>
        <div class="stat-card">
          <span class="stat-big">3</span><span class="stat-desc">今日新增</span>
        </div>
        <div class="stat-card">
          <span class="stat-big">7</span><span class="stat-desc">待审核</span>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>标题</th>
              <th>作者</th>
              <th>状态</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="post in mockPosts" :key="post.id">
              <td>{{ post.id }}</td>
              <td class="cell-title">{{ post.title }}</td>
              <td>{{ post.author }}</td>
              <td>
                <span :class="'status-tag ' + post.status">{{ post.statusLabel }}</span>
              </td>
              <td class="cell-time">{{ post.time }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 评论资产 -->
    <div v-if="activeTab === 'comments'" class="tab-content">
      <div class="stat-row">
        <div class="stat-card">
          <span class="stat-big">1,280</span><span class="stat-desc">总评论</span>
        </div>
        <div class="stat-card">
          <span class="stat-big">15</span><span class="stat-desc">今日新增</span>
        </div>
        <div class="stat-card">
          <span class="stat-big">3</span><span class="stat-desc">待审核</span>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>内容</th>
              <th>用户</th>
              <th>帖子</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in mockComments" :key="c.id">
              <td>{{ c.id }}</td>
              <td class="cell-title">{{ c.content }}</td>
              <td>{{ c.user }}</td>
              <td>{{ c.post }}</td>
              <td class="cell-time">{{ c.time }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 静态资产 -->
    <div v-if="activeTab === 'assets'" class="tab-content">
      <div class="stat-row">
        <div class="stat-card">
          <span class="stat-big">2,345</span><span class="stat-desc">总文件</span>
        </div>
        <div class="stat-card">
          <span class="stat-big">1.2GB</span><span class="stat-desc">总存储</span>
        </div>
        <div class="stat-card">
          <span class="stat-big">89MB</span><span class="stat-desc">本月新增</span>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>类型</th>
              <th>大小</th>
              <th>上传者</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in mockFiles" :key="f.id">
              <td class="cell-title">{{ f.name }}</td>
              <td>{{ f.type }}</td>
              <td>{{ f.size }}</td>
              <td>{{ f.uploader }}</td>
              <td class="cell-time">{{ f.time }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import { DocumentTextOutline, ChatbubblesOutline, ImageOutline } from '@vicons/ionicons5'

const tabs = [
  { key: 'posts', label: '帖子资产', icon: DocumentTextOutline },
  { key: 'comments', label: '评论资产', icon: ChatbubblesOutline },
  { key: 'assets', label: '静态资产', icon: ImageOutline }
]

const activeTab = ref('posts')

// 模拟数据
const mockPosts = [
  {
    id: 1,
    title: 'Vue3 组合式 API 实践指南',
    author: 'alice',
    status: 'published',
    statusLabel: '已发布',
    time: '2026-06-05'
  },
  {
    id: 2,
    title: '深入理解 TypeScript 类型系统',
    author: 'bob',
    status: 'published',
    statusLabel: '已发布',
    time: '2026-06-04'
  },
  {
    id: 3,
    title: 'Flask 异步任务队列最佳实践',
    author: 'charlie',
    status: 'pending',
    statusLabel: '待审核',
    time: '2026-06-06'
  },
  {
    id: 4,
    title: '前端性能优化实战记录',
    author: 'alice',
    status: 'pending',
    statusLabel: '待审核',
    time: '2026-06-06'
  },
  {
    id: 5,
    title: '微服务架构设计模式分析',
    author: 'dave',
    status: 'published',
    statusLabel: '已发布',
    time: '2026-06-03'
  }
]

const mockComments = [
  {
    id: 1,
    content: '写得很详细，学习了！',
    user: 'user1',
    post: 'Vue3 实践指南',
    time: '2026-06-05'
  },
  {
    id: 2,
    content: 'TypeScript 的高级类型确实很强大',
    user: 'user2',
    post: 'TS 类型系统',
    time: '2026-06-04'
  },
  {
    id: 3,
    content: '有没有 Docker 部署的方案？',
    user: 'user3',
    post: 'Flask 最佳实践',
    time: '2026-06-06'
  }
]

const mockFiles = [
  {
    id: 1,
    name: 'banner-home.png',
    type: '图片',
    size: '2.3MB',
    uploader: 'alice',
    time: '2026-06-05'
  },
  {
    id: 2,
    name: 'intro-video.mp4',
    type: '视频',
    size: '45MB',
    uploader: 'bob',
    time: '2026-06-04'
  },
  {
    id: 3,
    name: 'document.pdf',
    type: '文档',
    size: '1.1MB',
    uploader: 'charlie',
    time: '2026-06-06'
  },
  { id: 4, name: 'logo.svg', type: '图片', size: '128KB', uploader: 'alice', time: '2026-06-03' }
]
</script>

<style scoped>
.assets-page {
  max-width: 100%;
}
/* ── Tabs ── */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.tab-btn.active {
  background: var(--primary-light-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
  font-weight: 600;
}
.tab-btn:hover:not(.active) {
  background: var(--surface-strong-color);
}

/* ── Stats ── */
.stat-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card {
  flex: 1;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  text-align: center;
}
.stat-big {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}
.stat-desc {
  display: block;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

/* ── Table ── */
.table-wrap {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 10px 14px;
  background: var(--bg-color);
  color: var(--text-tertiary);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-color);
}
.data-table td {
  padding: 10px 14px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--divider-color);
}
.data-table tr:last-child td {
  border-bottom: none;
}
.cell-title {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-weight: 500;
}
.cell-time {
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

/* ── Status Tag ── */
.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.status-tag.published {
  background: rgba(79, 122, 87, 0.1);
  color: var(--success-color);
}
.status-tag.pending {
  background: rgba(185, 133, 41, 0.1);
  color: var(--warning-color);
}
</style>
