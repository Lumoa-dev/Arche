<template>
  <div class="login-page">
    <div class="login-shell">
      <aside class="login-visual" aria-hidden="true">
        <div class="visual-orb orb-a" />
        <div class="visual-orb orb-b" />
        <div class="visual-grid" />
        <div class="visual-badge badge-a">每日灵感 +{{ dailyInspiration }}</div>
        <div class="visual-badge badge-b">共创中 {{ onlineCreators }} 人</div>
        <div class="visual-badge badge-c">回放片段 {{ replaySnippets }}</div>
        <div class="visual-content">
          <p class="visual-tag">JINNIANZHI</p>
          <h2 class="visual-dynamic-title">
            {{ typedTitle }}
            <span v-if="typingPhase === 'title'" class="type-caret" aria-hidden="true" />
          </h2>
          <p>
            {{ typedDesc }}
            <span v-if="typingPhase === 'desc'" class="type-caret" aria-hidden="true" />
          </p>
        </div>
      </aside>

      <div class="login-card">
        <div class="card-header">
          <div class="logo-icon" :class="`lock-${lockFeedback}`">
            <component :is="lockIcon" />
          </div>
          <h2>欢迎回来</h2>
        </div>

        <NForm :model="formModel" :show-feedback="true" label-width="80">
          <NGrid :cols="1">
            <NFormItemGi label="账号" path="identity" :span="1">
              <ArInput v-model:value="formModel.identity" placeholder="请输入用户名或邮箱" />
            </NFormItemGi>
            <NFormItemGi label="密码" path="password" :span="1">
              <ArInput
                v-model:value="formModel.password"
                type="password"
                show-password-on="click"
                placeholder="请输入密码"
              />
            </NFormItemGi>
            <NFormItemGi v-if="useMockLogin" label="登录身份" path="role" :span="1">
              <NSelect
                v-model:value="formModel.role"
                :options="roleOptions"
                placeholder="请选择登录身份"
              />
            </NFormItemGi>
            <NGi :span="1" style="margin-top: 20px">
              <div class="form-action">
                <ArButton type="primary" size="lg" :loading="loading" @click="handleLogin">
                  立即登录
                </ArButton>
              </div>
            </NGi>
          </NGrid>
        </NForm>
        <div class="register-entry">还没账号？<RouterLink to="/register">立即注册</RouterLink></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NForm, NGrid, NGi, NSelect, NFormItemGi } from 'naive-ui'
import { useUserStore } from '@/lib/store/modules/user'
import { $message } from '@/lib/utils/message'
import { LockClosedOutline, LockOpenOutline } from '@/icons'
import ArInput from '@/components/ui/ArInput.vue'
import ArButton from '@/components/ui/ArButton.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const useMockLogin = import.meta.env.VITE_USE_MOCK_LOGIN === 'true'

const loading = ref(false)
const formModel = ref<{
  role: 'user' | 'admin' | 'guest'
  identity: string
  password: string
}>({
  role: 'user',
  identity: '',
  password: ''
})

const roleOptions = [
  { label: '普通用户', value: 'user' },
  { label: '管理员', value: 'admin' },
  { label: '访客', value: 'guest' }
]

const visualCopies = [
  {
    title: '把灵感写成可回放的时光片段',
    desc: '在这里记录表达、整理思绪、连接共创。每一次登录，都是一次新的出发。'
  },
  {
    title: '今天也值得留下一页新叙事',
    desc: '从一句话开始，把日常细节沉淀成你未来会感谢的证据。'
  },
  {
    title: '你写下的每一段，都在塑造长期作品',
    desc: '连续表达会形成独特风格，灵感不会凭空消失，它会被你训练出来。'
  }
]
const copyIndex = ref(0)
const dailyInspiration = ref(12)
const onlineCreators = ref(8)
const replaySnippets = ref(264)
const typedTitle = ref('')
const typedDesc = ref('')
const typingPhase = ref<'title' | 'desc' | 'pause'>('title')
const lockFeedback = ref<'idle' | 'success' | 'error'>('idle')
let typingTimer: number | null = null
let lockTimer: number | null = null

const lockIcon = computed(() =>
  lockFeedback.value === 'success' ? LockOpenOutline : LockClosedOutline
)

if (typeof route.query.identity === 'string') {
  formModel.value.identity = route.query.identity
}

const scheduleTyping = (delay: number) => {
  typingTimer = window.setTimeout(runTypewriter, delay)
}

const rollVisualMetrics = () => {
  dailyInspiration.value = Math.max(9, dailyInspiration.value + (Math.random() > 0.45 ? 1 : 0))
  onlineCreators.value = Math.max(5, onlineCreators.value + (Math.random() > 0.5 ? 1 : -1))
  replaySnippets.value = Math.max(180, replaySnippets.value + (Math.random() > 0.35 ? 2 : 1))
}

const runTypewriter = () => {
  const currentCopy = visualCopies[copyIndex.value] ?? visualCopies[0]
  if (!currentCopy) return
  if (typingPhase.value === 'title') {
    const nextLength = typedTitle.value.length + 1
    typedTitle.value = currentCopy.title.slice(0, nextLength)
    if (nextLength >= currentCopy.title.length) {
      typingPhase.value = 'desc'
      scheduleTyping(180)
      return
    }
    scheduleTyping(82)
    return
  }

  if (typingPhase.value === 'desc') {
    const nextLength = typedDesc.value.length + 1
    typedDesc.value = currentCopy.desc.slice(0, nextLength)
    if (nextLength >= currentCopy.desc.length) {
      typingPhase.value = 'pause'
      scheduleTyping(25000 + Math.floor(Math.random() * 5000))
      return
    }
    scheduleTyping(42)
    return
  }

  copyIndex.value = (copyIndex.value + 1) % visualCopies.length
  typedTitle.value = ''
  typedDesc.value = ''
  typingPhase.value = 'title'
  rollVisualMetrics()
  scheduleTyping(420)
}

const setLockFeedback = (state: 'idle' | 'success' | 'error') => {
  lockFeedback.value = state
  if (lockTimer !== null) {
    window.clearTimeout(lockTimer)
    lockTimer = null
  }
  if (state !== 'idle') {
    lockTimer = window.setTimeout(
      () => {
        lockFeedback.value = 'idle'
      },
      state === 'error' ? 900 : 2200
    )
  }
}

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

onMounted(() => {
  const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
  if (mq.matches) {
    const copy = visualCopies[0]!
    typedTitle.value = copy.title
    typedDesc.value = copy.desc
    typingPhase.value = 'pause'
  } else {
    runTypewriter()
  }
})

onBeforeUnmount(() => {
  if (typingTimer !== null) {
    window.clearTimeout(typingTimer)
  }
  if (lockTimer !== null) {
    window.clearTimeout(lockTimer)
  }
})

const handleLogin = async () => {
  loading.value = true
  try {
    if (useMockLogin) {
      await userStore.loginAsRole(formModel.value.role)
      setLockFeedback('success')
      $message.success(`欢迎回来，${formModel.value.role === 'admin' ? '管理员' : '用户'}`)
    } else {
      await userStore.login({
        identity: formModel.value.identity,
        password: formModel.value.password
      })
      setLockFeedback('success')
      $message.success(
        `欢迎回来，${userStore.userInfo?.nickname || userStore.userInfo?.username || '用户'}`
      )
    }
    await sleep(560)

    // 登录后统一回首页
    await router.push('/')
  } catch {
    setLockFeedback('error')
    $message.error('登录失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  padding: var(--spacing-xl) 0;
}

.login-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 16px;
  align-items: stretch;
}

.login-visual {
  position: relative;
  overflow: hidden;
  min-height: 506px;
  display: flex;
  align-items: flex-end;
  padding: 28px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.visual-content {
  position: relative;
  z-index: 2;
  max-width: 420px;
  display: grid;
  gap: 8px;
}

.visual-tag {
  margin: 0 0 10px;
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--text-tertiary);
}

.login-visual h2 {
  margin: 0 0 12px;
  font-size: 30px;
  line-height: 1.3;
  color: var(--text-primary);
  text-wrap: balance;
}

.type-caret {
  display: inline-block;
  margin-left: 2px;
  width: 2px;
  height: 0.95em;
  border-radius: 1px;
  background: color-mix(in srgb, var(--primary-color) 68%, transparent);
  animation: caret-blink 1.8s steps(1) infinite;
  vertical-align: -0.08em;
}

.login-visual p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.75;
  font-size: 14px;
  min-height: 52px;
}

.visual-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(0.4px);
  z-index: 0;
}

.orb-a {
  width: 220px;
  height: 220px;
  background: radial-gradient(
    circle at 30% 30%,
    color-mix(in srgb, var(--primary-color) 38%, transparent),
    color-mix(in srgb, var(--primary-color) 8%, transparent)
  );
  top: -36px;
  right: -40px;
  animation: drift-a 9s ease-in-out infinite;
}

.orb-b {
  width: 180px;
  height: 180px;
  background: radial-gradient(
    circle at 40% 35%,
    color-mix(in srgb, var(--accent-color) 28%, transparent),
    color-mix(in srgb, var(--accent-color) 6%, transparent)
  );
  left: -40px;
  bottom: 80px;
  animation: drift-b 11s ease-in-out infinite;
}

.visual-grid {
  position: absolute;
  inset: 0;
  z-index: 1;
  opacity: 0.28;
  background-image:
    linear-gradient(color-mix(in srgb, var(--primary-color) 12%, transparent) 1px, transparent 1px),
    linear-gradient(
      90deg,
      color-mix(in srgb, var(--primary-color) 10%, transparent) 1px,
      transparent 1px
    );
  background-size: 26px 26px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.55), transparent 85%);
}

.visual-badge {
  position: absolute;
  z-index: 2;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--primary-color) 26%, transparent);
  background: var(--surface-strong-color);
  color: var(--text-primary);
  font-size: 12px;
  line-height: 1;
  padding: 8px 12px;
}

.badge-a {
  top: 34px;
  left: 30px;
  animation: float-soft-a 8.5s ease-in-out infinite;
}

.badge-b {
  top: 92px;
  right: 42px;
  animation: float-soft-b 9.5s ease-in-out infinite;
}

.badge-c {
  bottom: 168px;
  right: 34px;
  animation: float-soft-c 10.5s ease-in-out infinite;
}

.login-card {
  padding: var(--spacing-2xl);
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.login-card :deep(.n-card) {
  background: var(--surface-color);
  border-color: var(--border-color);
}

.login-card :deep(.n-card-content) {
  background: var(--surface-color);
  border-radius: 12px;
}

.login-card :deep(.n-form-item-blank) {
  width: 100%;
}

.card-header {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.logo-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--primary-light-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  margin: 0 auto var(--spacing-md);
  transition:
    background-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.logo-icon svg {
  width: 32px;
  height: 32px;
  color: var(--primary-color);
  transform-origin: 50% 32%;
}

.logo-icon.lock-success {
  background: color-mix(in srgb, var(--success-color) 14%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--success-color) 18%, transparent) inset;
}

.logo-icon.lock-success svg {
  color: var(--success-color);
  animation: lock-open-pop 0.56s cubic-bezier(0.2, 0.7, 0.2, 1);
}

.logo-icon.lock-error {
  background: color-mix(in srgb, var(--error-color) 14%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--error-color) 16%, transparent) inset;
  animation: lock-error-shake 0.46s ease-in-out;
}

.logo-icon.lock-error svg {
  color: var(--error-color);
}

.card-header h2 {
  margin: 0 0 var(--spacing-xs) 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.register-entry {
  margin-top: 14px;
  text-align: center;
  color: var(--text-secondary);
}

.form-action {
  display: flex;
  justify-content: center;
}

.form-action .ar-button {
  min-width: 200px;
}

.register-entry a {
  color: var(--text-secondary);
  text-decoration: none;
  border-bottom: 1px solid var(--border-color);
  transition:
    color 0.2s ease,
    border-color 0.2s ease;
}

.register-entry a:hover {
  color: var(--text-primary);
  border-bottom-color: color-mix(in srgb, var(--text-primary) 42%, transparent);
}

@keyframes drift-a {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }
  50% {
    transform: translate3d(-10px, 14px, 0);
  }
}

@keyframes drift-b {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }
  50% {
    transform: translate3d(12px, -8px, 0);
  }
}

@keyframes float-soft-a {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }
  50% {
    transform: translate3d(0, -5px, 0);
  }
}

@keyframes float-soft-b {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }
  50% {
    transform: translate3d(0, 4px, 0);
  }
}

@keyframes float-soft-c {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }
  50% {
    transform: translate3d(0, -4px, 0);
  }
}

@keyframes caret-blink {
  0%,
  49% {
    opacity: 1;
  }
  50%,
  100% {
    opacity: 0;
  }
}

@keyframes lock-open-pop {
  0% {
    transform: translateY(0) rotate(0deg);
  }
  42% {
    transform: translateY(-7px) rotate(-9deg);
  }
  75% {
    transform: translateY(-5px) rotate(-14deg);
  }
  100% {
    transform: translateY(0) rotate(0deg);
  }
}

@keyframes lock-error-shake {
  0%,
  100% {
    transform: translateX(0);
  }
  20% {
    transform: translateX(-4px);
  }
  40% {
    transform: translateX(4px);
  }
  60% {
    transform: translateX(-3px);
  }
  80% {
    transform: translateX(3px);
  }
}

@media (max-width: 860px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .login-visual {
    min-height: 220px;
    padding: 20px;
  }

  .login-visual h2 {
    font-size: 24px;
  }
}

@media (max-width: 520px) {
  .login-page {
    max-width: 420px;
  }

  .login-visual {
    display: none;
  }
}
</style>
