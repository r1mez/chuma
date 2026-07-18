<template>
  <BorderGlow class="dashboard-page" background-color="transparent">
    <div class="content">Dashboard</div>
  </BorderGlow>
</template>

<script setup lang="ts">
import BorderGlow from '@/components/BorderGlow.vue'
</script>

<style scoped>
.dashboard-page {
  color: #eceef0;
  min-height: calc(100vh - 170px);
  margin: 20px;
}
.content {
  padding: 20px;
}
</style>
