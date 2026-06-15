<template>
  <ArPage>
    <ArVBox gap="var(--layout-gap)">
      <ArPageHeader title="素材库" desc="管理你的图片、视频和文件资源" />
      <ArCard
        variant="elevated"
        padding="lg"
        style="text-align: center; color: var(--text-tertiary)"
      >
        素材库功能开发中，敬请期待
      </ArCard>
    </ArVBox>
  </ArPage>
</template>

<script setup lang="ts">
import ArPage from '@/components/ui/ArPage.vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
</script>
