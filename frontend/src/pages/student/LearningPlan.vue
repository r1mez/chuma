<template>
  <BorderGlow class="learning-plan-page" background-color="transparent">
    <div class="content">LearningPlan</div>
  </BorderGlow>
</template>

<script setup lang="ts">
import BorderGlow from '@/components/BorderGlow.vue'
</script>

<style scoped>
.learning-plan-page {
  color: #eceef0;
  min-height: calc(100vh - 170px);
  margin: 20px;
}
.content {
  padding: 20px;
}
</style>
