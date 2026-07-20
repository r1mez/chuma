<template>
  <BorderGlow class="subject-records-page" background-color="transparent">
    <div class="content">学科做题记录详细占位页</div>
  </BorderGlow>
</template>

<script setup lang="ts">
import BorderGlow from '@/components/BorderGlow.vue'
</script>

<style scoped>
.subject-records-page {
  color: #000;
  min-height: calc(100vh - 170px);
  margin: 20px;
}
.content {
  padding: 20px;
}
</style>