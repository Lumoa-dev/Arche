<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useUserStore } from '@/lib/store/modules/user'
import ArButton from '@/components/ui/ArButton.vue'
import ArTag from '@/components/ui/ArTag.vue'
import ArAvatar from '@/components/ui/ArAvatar.vue'
import ArCard from '@/components/ui/ArCard.vue'

const router = useRouter()
const message = useMessage()
const userStore = useUserStore()

const showLogoutModal = ref(false)

const handleLogout = async () => {
  try {
    await userStore.logout()
    message.success('退出登录成功')
    await router.push('/login')
  } catch {
    message.error('退出登录失败')
  } finally {
    showLogoutModal.value = false
  }
}
</script>

<template>
  <div class="profile-page">
    <div class="page-heading">
      <h2>个人资料</h2>
    </div>

    <!-- 头部：头像 + 用户信息 -->
    <ArCard padding="lg" class="profile-header-card">
      <div class="profile-header">
        <ArAvatar
          :avatar-url="userStore.userInfo?.avatar || ''"
          :username="userStore.userInfo?.username || ''"
          :size="64"
          :clickable="false"
        />
        <div class="header-info">
          <div class="header-name-row">
            <span class="header-username">{{ userStore.userInfo?.username || '-' }}</span>
            <span v-if="userStore.userInfo?.nickname" class="header-nickname">
              （{{ userStore.userInfo.nickname }}）
            </span>
            <ArTag
              :color="(userStore.userInfo?.level ?? 5) === 0 ? 'red' : 'primary'"
              type="light"
              size="sm"
              class="header-tag"
            >
              {{ (userStore.userInfo?.level ?? 5) === 0 ? '管理员' : '普通用户' }}
            </ArTag>
          </div>
          <p v-if="userStore.userInfo?.bio" class="header-bio">{{ userStore.userInfo.bio }}</p>
        </div>
      </div>
    </ArCard>

    <!-- 信息卡片区 -->
    <ArCard padding="lg">
      <h3 class="section-title">基本信息</h3>
      <div class="info-grid-2col">
        <div class="info-item">
          <span class="info-label">邮箱</span>
          <span class="info-value">{{ userStore.userInfo?.email || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">权限</span>
          <span class="info-value">
            {{
              userStore.userInfo?.permissions?.length
                ? `${userStore.userInfo.permissions.length} 项权限`
                : '无权限'
            }}
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">注册时间</span>
          <span class="info-value">{{ userStore.userInfo?.created_at?.slice(0, 10) || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">生日</span>
          <span class="info-value">{{ userStore.userInfo?.birthday || '-' }}</span>
        </div>
      </div>
    </ArCard>

    <!-- 统计数据区 -->
    <ArCard padding="lg">
      <h3 class="section-title">数据统计</h3>
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-value">0</span>
          <span class="stat-label">发帖数</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">0</span>
          <span class="stat-label">阅读量</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">0</span>
          <span class="stat-label">点赞数</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">0</span>
          <span class="stat-label">收藏数</span>
        </div>
      </div>
    </ArCard>

    <!-- 退出登录 -->
    <div class="action-section">
      <ArButton type="danger" @click="showLogoutModal = true">退出登录</ArButton>
    </div>

    <!-- 退出确认弹窗 -->
    <Teleport to="body">
      <div v-if="showLogoutModal" class="modal-overlay" @click.self="showLogoutModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <span class="modal-title">确认退出</span>
          </div>
          <div class="modal-body">
            <p>确定要退出当前账号吗？</p>
          </div>
          <div class="modal-footer">
            <ArButton type="ghost" @click="showLogoutModal = false">取消</ArButton>
            <ArButton type="danger" @click="handleLogout">确认</ArButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.page-heading {
  margin-bottom: 0;
}

.page-heading h2 {
  margin: 0;
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

/* ── 头部卡片 ── */
.profile-header-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.header-name-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.header-username {
  font-size: 22px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.header-nickname {
  font-size: 15px;
  color: var(--text-tertiary);
}

.header-tag {
  flex-shrink: 0;
}

.header-bio {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* ── 信息卡片 ── */
.section-title {
  margin: 0 0 var(--spacing-md);
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.info-grid-2col {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--spacing-sm) 0;
}

.info-item .info-label {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
}

.info-item .info-value {
  font-size: 14px;
  color: var(--text-primary);
}

/* ── 统计数据 ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: var(--spacing-lg);
  background: var(--surface-inset-color);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.stat-value {
  font-size: 26px;
  font-weight: var(--font-weight-bold);
  color: var(--primary-color);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ── 退出按钮 ── */
.action-section {
  display: flex;
  justify-content: center;
  padding-top: var(--spacing-sm);
}

/* ── 模态框 ── */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(26, 24, 23, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: 400px;
  max-width: 90vw;
}

.modal-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--divider-color);
}

.modal-title {
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--spacing-lg);
}

.modal-body p {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--divider-color);
}

@media (max-width: 680px) {
  .info-grid-2col {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .profile-header {
    flex-direction: column;
    text-align: center;
  }

  .header-name-row {
    justify-content: center;
  }
}
</style>
