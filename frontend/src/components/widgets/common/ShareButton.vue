<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { ShareSocialOutline } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'

withDefaults(
  defineProps<{
    disabled?: boolean
  }>(),
  {
    disabled: false
  }
)

const message = useMessage()

function handleShare() {
  const url = window.location.href
  navigator.clipboard
    .writeText(url)
    .then(() => {
      message.success('链接已复制到剪贴板')
    })
    .catch(() => {
      message.error('复制失败')
    })
}
</script>

<template>
  <button
    :class="['share-btn', { 'is-disabled': disabled }]"
    :disabled="disabled"
    aria-label="分享"
    @click="handleShare"
  >
    <NIcon size="18">
      <ShareSocialOutline />
    </NIcon>
    <span class="share-label">分享</span>
  </button>
</template>

<style scoped>
.share-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition:
    color var(--transition-fast),
    background-color var(--transition-fast);
  touch-action: manipulation;
}

.share-btn:hover:not(.is-disabled) {
  color: var(--primary-color);
  background: var(--primary-light-color);
}

.share-btn.is-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.share-label {
  font-weight: var(--font-weight-medium);
}
</style>
