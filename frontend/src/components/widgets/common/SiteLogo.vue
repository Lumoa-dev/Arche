<template>
  <RouterLink to="/" class="site-logo" :class="[`site-logo--${size}`]">
    <img class="logo-mark" src="/logo-样式 (1).png" alt="锦年志 Logo" width="34" height="34" />
    <span class="logo-text">锦年志</span>
  </RouterLink>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: 'sm' | 'md'
  }>(),
  {
    size: 'md'
  }
)
</script>

<style scoped>
.site-logo {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: inherit;
}

.logo-mark {
  width: 34px;
  height: 34px;
  display: block;
  object-fit: cover;
  border-radius: 999px;
  border: 2px solid var(--surface-strong-color);
  box-shadow: 0 4px 12px var(--paper-shadow-color);
  flex-shrink: 0;
}

.logo-text {
  font-weight: 700;
  font-size: 20px;
  letter-spacing: 0.5px;
  background: linear-gradient(120deg, var(--primary-color) 0%, var(--accent-color) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.site-logo--sm .logo-mark {
  width: 28px;
  height: 28px;
}

.site-logo--sm .logo-text {
  font-size: 17px;
}
</style>
