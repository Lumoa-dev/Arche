<template>
  <ArPage>
    <ArVBox gap="var(--layout-gap)">
      <ArPageHeader title="GitHub" desc="项目开源仓库，欢迎 Star 和贡献" />
      <ArCard variant="elevated" padding="lg" style="text-align: center; color: var(--text-tertiary);">
        <p>正在跳转到 GitHub...</p>
        <a :href="repoUrl" target="_blank" rel="noopener noreferrer" style="display: inline-block; margin-top: 8px; color: var(--primary-color); text-decoration: none;">
          {{ repoUrl }}
        </a>
      </ArCard>
    </ArVBox>
  </ArPage>
</template>

<script setup lang="ts">
import ArPage from '@/components/ui/ArPage.vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import { onMounted } from 'vue'

const repoUrl = 'https://github.com/jamnodesmith/Arche'

onMounted(() => {
  window.open(repoUrl, '_blank', 'noopener')
})
</script>
