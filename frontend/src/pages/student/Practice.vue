<template>
  <BorderGlow class="practice-page" background-color="transparent">
    <div class="content">Practice</div>
  </BorderGlow>
</template>

<script setup lang="ts">
import BorderGlow from '@/components/BorderGlow.vue'
</script>

<style scoped>
.practice-page {
  color: #eceef0;
  min-height: calc(100vh - 40px);
  margin: 20px;
}
.content {
  padding: 20px;
}
</style>
