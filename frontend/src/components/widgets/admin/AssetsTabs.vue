<script setup lang="ts">
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import { DocumentTextOutline, ChatbubblesOutline, ImageOutline } from '@vicons/ionicons5'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import ArCard from '@/components/ui/ArCard.vue'
import StatCard from '@/components/widgets/admin/StatCard.vue'

const tabs = [
  { key: 'posts', label: '帖子资产', icon: DocumentTextOutline },
  { key: 'comments', label: '评论资产', icon: ChatbubblesOutline },
  { key: 'assets', label: '静态资产', icon: ImageOutline }
]

const activeTab = ref('posts')

const mockPosts = [
  { id: 1, title: 'Vue3 组合式 API 实践指南', author: 'alice', status: 'published', statusLabel: '已发布', time: '2026-06-05' },
  { id: 2, title: '深入理解 TypeScript 类型系统', author: 'bob', status: 'published', statusLabel: '已发布', time: '2026-06-04' },
  { id: 3, title: 'Flask 异步任务队列最佳实践', author: 'charlie', status: 'pending', statusLabel: '待审核', time: '2026-06-06' },
  { id: 4, title: '前端性能优化实战记录', author: 'alice', status: 'pending', statusLabel: '待审核', time: '2026-06-06' },
  { id: 5, title: '微服务架构设计模式分析', author: 'dave', status: 'published', statusLabel: '已发布', time: '2026-06-03' }
]

const mockComments = [
  { id: 1, content: '写得很详细，学习了！', user: 'user1', post: 'Vue3 实践指南', time: '2026-06-05' },
  { id: 2, content: 'TypeScript 的高级类型确实很强大', user: 'user2', post: 'TS 类型系统', time: '2026-06-04' },
  { id: 3, content: '有没有 Docker 部署的方案？', user: 'user3', post: 'Flask 最佳实践', time: '2026-06-06' }
]

const mockFiles = [
  { id: 1, name: 'banner-home.png', type: '图片', size: '2.3MB', uploader: 'alice', time: '2026-06-05' },
  { id: 2, name: 'intro-video.mp4', type: '视频', size: '45MB', uploader: 'bob', time: '2026-06-04' },
  { id: 3, name: 'document.pdf', type: '文档', size: '1.1MB', uploader: 'charlie', time: '2026-06-06' },
  { id: 4, name: 'logo.svg', type: '图片', size: '128KB', uploader: 'alice', time: '2026-06-03' }
]

function statusClass(status: string) {
  return status === 'published' ? 'tag tag--published' : 'tag tag--pending'
}
function statusLabel(label: string) {
  return label
}
</script>

<template>
  <div>
    <ArPageHeader title="资源管理" desc="管理用户产生的帖子、评论和静态文件" />

    <div class="tabs">
      <button v-for="tab in tabs" :key="tab.key" :class="['tab', { 'tab--active': activeTab === tab.key }]" @click="activeTab = tab.key">
        <NIcon size="16"><component :is="tab.icon" /></NIcon>
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <!-- 帖子资产 -->
    <div v-if="activeTab === 'posts'">
      <ArVBox gap="16px">
        <ArHBox gap="16px">
          <StatCard label="总帖子" value="456" style="flex:1;" />
          <StatCard label="今日新增" value="3" style="flex:1;" />
          <StatCard label="待审核" value="7" style="flex:1;" />
        </ArHBox>
        <ArCard variant="elevated" style="overflow: hidden;">
          <table class="table">
            <thead><tr><th>ID</th><th>标题</th><th>作者</th><th>状态</th><th>时间</th></tr></thead>
            <tbody>
              <tr v-for="post in mockPosts" :key="post.id">
                <td>{{ post.id }}</td><td class="cell-title">{{ post.title }}</td><td>{{ post.author }}</td>
                <td><span :class="statusClass(post.status)">{{ post.statusLabel }}</span></td>
                <td class="cell-time">{{ post.time }}</td>
              </tr>
            </tbody>
          </table>
        </ArCard>
      </ArVBox>
    </div>

    <!-- 评论资产 -->
    <div v-if="activeTab === 'comments'">
      <ArVBox gap="16px">
        <ArHBox gap="16px">
          <StatCard label="总评论" value="1,280" style="flex:1;" />
          <StatCard label="今日新增" value="15" style="flex:1;" />
          <StatCard label="待审核" value="3" style="flex:1;" />
        </ArHBox>
        <ArCard variant="elevated" style="overflow: hidden;">
          <table class="table">
            <thead><tr><th>ID</th><th>内容</th><th>用户</th><th>帖子</th><th>时间</th></tr></thead>
            <tbody>
              <tr v-for="c in mockComments" :key="c.id">
                <td>{{ c.id }}</td><td class="cell-title">{{ c.content }}</td><td>{{ c.user }}</td><td>{{ c.post }}</td><td class="cell-time">{{ c.time }}</td>
              </tr>
            </tbody>
          </table>
        </ArCard>
      </ArVBox>
    </div>

    <!-- 静态资产 -->
    <div v-if="activeTab === 'assets'">
      <ArVBox gap="16px">
        <ArHBox gap="16px">
          <StatCard label="总文件" value="2,345" style="flex:1;" />
          <StatCard label="总存储" value="1.2GB" style="flex:1;" />
          <StatCard label="本月新增" value="89MB" style="flex:1;" />
        </ArHBox>
        <ArCard variant="elevated" style="overflow: hidden;">
          <table class="table">
            <thead><tr><th>文件名</th><th>类型</th><th>大小</th><th>上传者</th><th>时间</th></tr></thead>
            <tbody>
              <tr v-for="f in mockFiles" :key="f.id">
                <td class="cell-title">{{ f.name }}</td><td>{{ f.type }}</td><td>{{ f.size }}</td><td>{{ f.uploader }}</td><td class="cell-time">{{ f.time }}</td>
              </tr>
            </tbody>
          </table>
        </ArCard>
      </ArVBox>
    </div>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.tab {
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
  font-family: inherit;
}
.tab--active {
  background: var(--primary-light-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
  font-weight: 600;
}
.tab:hover:not(.tab--active) {
  background: var(--surface-strong-color);
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table th {
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
.table td {
  padding: 10px 14px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--divider-color);
}
.table tr:last-child td {
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
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.tag--published {
  background: rgba(79, 122, 87, 0.1);
  color: var(--success-color);
}
.tag--pending {
  background: rgba(185, 133, 41, 0.1);
  color: var(--warning-color);
}
</style>
