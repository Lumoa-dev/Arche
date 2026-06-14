<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { BookmarkOutline, Bookmark } from '@vicons/ionicons5'

withDefaults(
  defineProps<{
    active?: boolean
    disabled?: boolean
  }>(),
  {
    active: false,
    disabled: false
  }
)

const emit = defineEmits<{
  toggle: []
}>()

function handleClick() {
  emit('toggle')
}
</script>

<template>
  <button
    :class="['fav-btn', { 'is-active': active, 'is-disabled': disabled }]"
    :disabled="disabled"
    :aria-label="active ? '取消收藏' : '收藏'"
    :aria-pressed="active"
    @click="handleClick"
  >
    <NIcon size="18" class="fav-icon">
      <component :is="active ? Bookmark : BookmarkOutline" />
    </NIcon>
    <span class="fav-label">{{ active ? '已收藏' : '收藏' }}</span>
  </button>
</template>

<style scoped>
.fav-btn {
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

.fav-btn:hover:not(.is-disabled) {
  background: rgba(212, 160, 23, 0.08);
  color: var(--accent-yellow);
}

.fav-btn.is-active {
  color: var(--accent-yellow);
}

.fav-btn.is-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.fav-icon {
  transition: transform 0.3s var(--ease-out-spring);
}

.fav-btn:not(.is-disabled):active .fav-icon {
  animation: fav-bounce 0.3s var(--ease-out-spring);
}

.fav-label {
  font-weight: var(--font-weight-medium);
}

@keyframes fav-bounce {
  0% {
    transform: scale(1);
  }
  40% {
    transform: scale(1.25);
  }
  70% {
    transform: scale(0.9);
  }
  100% {
    transform: scale(1);
  }
}
</style>
