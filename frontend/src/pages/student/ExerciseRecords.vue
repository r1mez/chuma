<template>
  <BorderGlow class="exercise-records-page" background-color="transparent">
    <div class="content">做题记录</div>
  </BorderGlow>
</template>

<script setup lang="ts">
import BorderGlow from '@/components/BorderGlow.vue'
</script>

<style scoped>
.exercise-records-page {
  color: #000;
  min-height: calc(100vh - 170px);
  margin: 20px;
}
.content {
  padding: 20px;
}
</style>
