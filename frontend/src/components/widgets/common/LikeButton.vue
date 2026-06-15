<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { HeartOutline, Heart } from '@vicons/ionicons5'

withDefaults(
  defineProps<{
    count?: number
    active?: boolean
    disabled?: boolean
  }>(),
  {
    count: 0,
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
    :class="['like-btn', { 'is-active': active, 'is-disabled': disabled }]"
    :disabled="disabled"
    :aria-label="active ? '取消点赞' : '点赞'"
    :aria-pressed="active"
    @click="handleClick"
  >
    <NIcon size="18" class="like-icon">
      <component :is="active ? Heart : HeartOutline" />
    </NIcon>
    <span v-if="count !== undefined" class="like-count">{{ count }}</span>
  </button>
</template>

<style scoped>
.like-btn {
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
    background-color var(--transition-fast),
    transform var(--transition-fast);
  touch-action: manipulation;
}

.like-btn:hover:not(.is-disabled) {
  background: rgba(194, 58, 43, 0.08);
  color: var(--accent-red);
}

.like-btn:active:not(.is-disabled) {
  transform: scale(0.92);
}

.like-btn.is-active {
  color: var(--accent-red);
}

.like-btn.is-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.like-icon {
  transition: transform 0.2s var(--ease-out-spring);
}

.like-btn:not(.is-disabled):active .like-icon {
  animation: like-pop 0.2s var(--ease-out-spring);
}

.like-count {
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-medium);
}

@keyframes like-pop {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    transform: scale(1);
  }
}
</style>
