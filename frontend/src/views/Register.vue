<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NGrid, NGi, NFormItemGi, type FormRules } from 'naive-ui'
import ArInput from '@/components/ui/ArInput.vue'
import ArButton from '@/components/ui/ArButton.vue'
import { registerApi } from '@/components/logic/api'
import { $message } from '@/lib/utils/message'
import { LockClosedOutline } from '@/icons'

const router = useRouter()
const loading = ref(false)

const formModel = reactive({
  email: '',
  username: '',
  password: '',
  confirmPassword: ''
})

const rules: FormRules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    {
      required: true,
      message: '请再次输入密码',
      trigger: 'blur'
    },
    {
      validator: () => formModel.password === formModel.confirmPassword,
      message: '两次密码不一致',
      trigger: 'blur'
    }
  ]
}

type RegisterStage = { title: string; desc: string }

const registerStages: RegisterStage[] = [
  { title: '创建账号', desc: '填写基础信息，建立你的创作身份。' },
  { title: '完善资料', desc: '补充昵称与偏好，让主页更有个人风格。' },
  { title: '开始发布', desc: '写下第一篇内容，建立你的长期作品库。' }
]
const stageIndex = ref(0)
const currentStage = computed((): RegisterStage => {
  const i = stageIndex.value % registerStages.length
  return registerStages[i] ?? registerStages[0]!
})
let stageTimer: number | null = null

onMounted(() => {
  stageTimer = window.setInterval(() => {
    stageIndex.value = (stageIndex.value + 1) % registerStages.length
  }, 3200)
})

onBeforeUnmount(() => {
  if (stageTimer !== null) {
    window.clearInterval(stageTimer)
  }
})

const handleRegister = async () => {
  loading.value = true
  try {
    await registerApi({
      email: formModel.email,
      username: formModel.username,
      nickname: formModel.username,
      password: formModel.password
    })
    $message.success('注册成功，请登录')
    await router.push({
      path: '/login',
      query: { identity: formModel.email || formModel.username }
    })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-shell">
      <aside class="register-visual" aria-hidden="true">
        <div class="visual-orb orb-a" />
        <div class="visual-orb orb-b" />
        <div class="visual-grid" />
        <div class="register-visual-content">
          <p class="visual-tag">ONBOARDING FLOW</p>
          <h2>{{ currentStage.title }}</h2>
          <p>{{ currentStage.desc }}</p>
          <div class="stage-track">
            <div
              v-for="(stage, index) in registerStages"
              :key="stage.title"
              class="stage-item"
              :class="{ active: index === stageIndex, done: index < stageIndex }"
            >
              <span class="dot" />
              <span class="text">{{ stage.title }}</span>
            </div>
          </div>
        </div>
      </aside>

      <div class="register-card">
        <div class="card-header">
          <div class="logo-icon"><LockClosedOutline /></div>
          <h2>创建账号</h2>
          <p>注册后即可发布和管理你的博客内容</p>
        </div>

        <NForm :model="formModel" :rules="rules" label-width="80">
          <NGrid :cols="1">
            <NFormItemGi label="邮箱" path="email"
              ><ArInput v-model:value="formModel.email" placeholder="请输入邮箱"
            /></NFormItemGi>
            <NFormItemGi label="用户名" path="username"
              ><ArInput v-model:value="formModel.username" placeholder="请输入用户名"
            /></NFormItemGi>
            <NFormItemGi label="密码" path="password">
              <ArInput
                v-model:value="formModel.password"
                type="password"
                show-password-on="click"
                placeholder="请输入密码"
              />
            </NFormItemGi>
            <NFormItemGi label="确认密码" path="confirmPassword">
              <ArInput
                v-model:value="formModel.confirmPassword"
                type="password"
                show-password-on="click"
                placeholder="请再次输入密码"
              />
            </NFormItemGi>
            <NGi :span="1" style="margin-top: 20px">
              <div class="form-action">
                <ArButton type="primary" size="lg" :loading="loading" @click="handleRegister"
                  >立即注册</ArButton
                >
              </div>
            </NGi>
          </NGrid>
        </NForm>

        <div class="bottom">已有账号？<RouterLink to="/login">去登录</RouterLink></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  padding: 0;
}

.register-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 16px;
  align-items: stretch;
}

.register-visual {
  position: relative;
  overflow: hidden;
  min-height: 480px;
  padding: 24px;
  display: flex;
  align-items: flex-end;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.register-visual-content {
  position: relative;
  z-index: 2;
  max-width: 420px;
  display: grid;
  gap: 10px;
}

.visual-tag {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--text-tertiary);
}

.register-visual h2 {
  margin: 0;
  font-size: 30px;
  line-height: 1.3;
  color: var(--text-primary);
}

.register-visual p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
  font-size: 14px;
}

.visual-orb {
  position: absolute;
  border-radius: 999px;
  z-index: 0;
}

.orb-a {
  width: 220px;
  height: 220px;
  top: -44px;
  right: -44px;
  background: radial-gradient(
    circle at 30% 30%,
    color-mix(in srgb, var(--primary-color) 36%, transparent),
    color-mix(in srgb, var(--primary-color) 8%, transparent)
  );
  animation: drift-a 8.8s ease-in-out infinite;
}

.orb-b {
  width: 180px;
  height: 180px;
  left: -38px;
  bottom: 88px;
  background: radial-gradient(
    circle at 40% 35%,
    color-mix(in srgb, var(--accent-color) 26%, transparent),
    color-mix(in srgb, var(--accent-color) 6%, transparent)
  );
  animation: drift-b 10.8s ease-in-out infinite;
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
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.58), transparent 86%);
}

.stage-track {
  margin-top: 6px;
  display: grid;
  gap: 10px;
}

.stage-item {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  color: var(--text-secondary);
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  transition: all 0.24s ease;
}

.stage-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary-color) 30%, transparent);
  transition: inherit;
}

.stage-item .text {
  font-size: 12px;
  line-height: 1;
}

.stage-item.active {
  color: var(--text-primary);
  border-color: color-mix(in srgb, var(--primary-color) 30%, transparent);
  background: var(--surface-color);
  transform: translateX(6px);
}

.stage-item.active .dot {
  background: color-mix(in srgb, var(--primary-color) 82%, transparent);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--primary-color) 14%, transparent);
}

.stage-item.done {
  border-color: color-mix(in srgb, var(--success-color) 24%, transparent);
  color: var(--success-color);
}

.stage-item.done .dot {
  background: color-mix(in srgb, var(--success-color) 74%, transparent);
}

.register-card {
  padding: var(--spacing-2xl);
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  animation: register-card-enter 0.38s ease both;
}

.register-card :deep(.n-card) {
  background: var(--surface-color);
  border-color: var(--border-color);
}

.register-card :deep(.n-card-content) {
  background: var(--surface-color);
  border-radius: 12px;
}

.register-card :deep(.n-form-item-blank) {
  width: 100%;
}
.card-header {
  text-align: center;
  margin-bottom: var(--spacing-md);
}
.logo-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: var(--primary-light-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  animation: logo-soft-float 3.2s ease-in-out infinite;
}
.logo-icon :deep(svg) {
  width: 30px;
  height: 30px;
  color: var(--primary-color);
}
.card-header h2 {
  margin-bottom: 8px;
}
.card-header p {
  color: var(--text-secondary);
}
.bottom {
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

.bottom a {
  color: var(--text-secondary);
  text-decoration: none;
  border-bottom: 1px solid var(--border-color);
  transition:
    color 0.2s ease,
    border-color 0.2s ease;
}

.bottom a:hover {
  color: var(--text-primary);
  border-bottom-color: color-mix(in srgb, var(--text-primary) 42%, transparent);
}

@keyframes register-card-enter {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes logo-soft-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
}

@keyframes drift-a {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }
  50% {
    transform: translate3d(-10px, 12px, 0);
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

@media (max-width: 860px) {
  .register-shell {
    grid-template-columns: 1fr;
  }

  .register-visual {
    min-height: 220px;
    padding: 20px;
  }

  .register-visual h2 {
    font-size: 24px;
  }
}

@media (max-width: 520px) {
  .register-page {
    max-width: 420px;
  }

  .register-visual {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .logo-icon {
    animation: none !important;
  }
  .visual-orb {
    animation: none !important;
  }
}
</style>
